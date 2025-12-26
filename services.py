import redis
import json
import hashlib
import asyncio
import aiohttp
from typing import List, Dict, Any
from config import config
from prompts import prompts
from database import Session, Place, User, Review
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging

from mistral_client import MistralClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        try:
            self.redis = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                decode_responses=True
            )
            self.redis.ping()
            logger.info("✅ Redis подключен")
        except redis.ConnectionError:
            logger.warning("⚠️ Redis не подключен. Кэш отключен.")
            self.redis = None
    
    def get_cache_key(self, prefix: str, query: str) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"{prefix}:{query_hash}"
    
    def get(self, key: str):
        if not self.redis:
            return None
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def set(self, key: str, data, ttl: int = 300):
        if self.redis:
            self.redis.setex(key, ttl, json.dumps(data))
    
    def set_url_content(self, url: str, content: str, ttl: int = 3600):
        if self.redis:
            key = f"url:{hashlib.md5(url.encode()).hexdigest()}"
            self.redis.setex(key, ttl, content)
    
    def get_url_content(self, url: str):
        if not self.redis:
            return None
        key = f"url:{hashlib.md5(url.encode()).hexdigest()}"
        return self.redis.get(key)
    
    def clear_all(self):
        """Очищает весь кэш Redis"""
        if self.redis:
            self.redis.flushall()
            return True
        return False

class WebParser:
    """Асинхронный парсер веб-сайтов"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_url(self, url: str) -> str:
        """Асинхронно загружает страницу"""
        try:
            async with self.session.get(url, timeout=10, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"⚠️ Ошибка загрузки {url}: статус {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {url}: {e}")
            return ""
    
    def parse_page_content(self, html: str, url: str) -> Dict[str, Any]:
        """Парсит контент страницы"""
        try:
            if not html:
                return {"url": url, "content": "", "title": "Ошибка загрузки"}
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe']):
                tag.decompose()
            
            title = self._extract_title(soup, url)
            content = self._extract_main_content(soup)
            contacts = self._extract_contacts(content)
            clean_content = self._clean_text(content)
            
            return {
                "url": url,
                "title": title,
                "content": clean_content[:3000],
                "contacts": contacts,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {url}: {e}")
            return {"url": url, "content": "", "title": "Ошибка парсинга"}
    
    def _extract_title(self, soup, url: str) -> str:
        selectors = [
            'h1',
            'title',
            'meta[property="og:title"]',
            '.title',
            '.page-title',
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if selector.startswith('meta'):
                        title = element.get('content', '').strip()
                    else:
                        title = element.get_text().strip()
                    
                    if title and len(title) > 3:
                        return title
            except:
                continue
        
        return url.split('//')[-1].split('/')[0].replace('www.', '').capitalize()
    
    def _extract_main_content(self, soup) -> str:
        content_selectors = [
            'main',
            'article',
            '.content',
            '.article-content',
            '#content',
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                texts = [elem.get_text().strip() for elem in elements]
                combined = ' '.join(texts)
                if len(combined) > 100:
                    return combined
        
        paragraphs = soup.find_all('p')
        texts = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
        return ' '.join(texts[:10])
    
    def _extract_contacts(self, text: str) -> Dict[str, str]:
        contacts = {
            "address": self._find_pattern(text, r'ул\.?\s+[\w\s\d\-]+,\s*\d+|[А-Яа-я][^,\n]{10,50},\s*\d+'),
            "phone": self._find_pattern(text, r'\+7\s?\(?\d{3}\)?\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'),
            "email": self._find_pattern(text, r'[\w\.-]+@[\w\.-]+\.\w+'),
        }
        
        return {k: v if v else "Не указано" for k, v in contacts.items()}
    
    def _find_pattern(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?;:()-]', '', text)
        return text.strip()

class LLMService:
    def __init__(self):
        self.client = MistralClient()
        self.cache = CacheService()
        self.url_database = config.URL_DATABASE
    
    def analyze_preferences(self, text: str) -> Dict[str, Any]:
        """Анализирует предпочтения"""
        cache_key = self.cache.get_cache_key("pref", text)
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        categories = list(self.url_database.keys())
        result = self.client.analyze_preferences(text, categories)
        
        self.cache.set(cache_key, result, ttl=1800)
        return result
    
    async def get_recommendations(self, categories: List[str]) -> str:
        """Получает рекомендации"""
        cache_key = self.cache.get_cache_key("rec", str(categories))
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        urls_to_parse = []
        for category in categories:
            if category in self.url_database:
                urls_to_parse.extend(self.url_database[category][:3])
        
        if not urls_to_parse:
            return "К сожалению, по выбранным категориям нет информации."
        
        parsed_data = await self._parse_urls_async(urls_to_parse)
        recommendations = self.client.generate_recommendations(parsed_data, categories)
        
        self.cache.set(cache_key, recommendations, ttl=3600)
        return recommendations
    
    async def _parse_urls_async(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Асинхронно парсит список URL"""
        parsed_results = []
        
        async with WebParser() as parser:
            tasks = [parser.fetch_url(url) for url in urls]
            html_contents = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, html in zip(urls, html_contents):
                if isinstance(html, Exception):
                    parsed_results.append({
                        "url": url,
                        "content": "",
                        "title": "Ошибка загрузки"
                    })
                else:
                    parsed = parser.parse_page_content(html, url)
                    parsed_results.append(parsed)
                    
                    if parsed["content"]:
                        self.cache.set_url_content(url, parsed["content"])
        
        successful = [p for p in parsed_results if p.get("content") and len(p["content"]) > 50]
        logger.info(f"✅ Успешно распарсено {len(successful)} из {len(urls)} сайтов")
        return successful
    
    def get_available_categories(self) -> List[str]:
        """Возвращает список категорий"""
        return list(self.url_database.keys())

class AdminService:
    @staticmethod
    def add_url_to_category(category: str, url: str):
        """Добавляет ссылку в базу"""
        if category in config.URL_DATABASE:
            if url not in config.URL_DATABASE[category]:
                config.URL_DATABASE[category].append(url)
                logger.info(f"✅ Добавлена ссылка: {category} - {url}")
                return True
        return False
    
    @staticmethod
    def get_url_stats() -> Dict[str, Any]:
        """Статистика по ссылкам"""
        stats = {}
        for category, urls in config.URL_DATABASE.items():
            stats[category] = len(urls)
        return stats
    
    @staticmethod
    def get_detailed_stats() -> Dict[str, Any]:
        """Подробная статистика"""
        stats = {}
        
        with Session() as session:
            stats['total_users'] = session.query(User).count()
            stats['total_admins'] = session.query(User).filter_by(role='admin').count()
            stats['total_places'] = session.query(Place).count()
            stats['active_places'] = session.query(Place).filter_by(is_active=True).count()
            stats['total_reviews'] = session.query(Review).count()
            stats['moderated_reviews'] = session.query(Review).filter_by(is_moderated=True).count()
        
        return stats