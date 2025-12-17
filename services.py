import redis
import json
import hashlib
import asyncio
import aiohttp
from mistralai import Mistral
from config import config
from database import Session, Place
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict, Any
import logging

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
        """Кэширует контент страницы"""
        if self.redis:
            key = f"url:{hashlib.md5(url.encode()).hexdigest()}"
            self.redis.setex(key, ttl, content)
    
    def get_url_content(self, url: str):
        """Получает контент страницы из кэша"""
        if not self.redis:
            return None
        key = f"url:{hashlib.md5(url.encode()).hexdigest()}"
        return self.redis.get(key)

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
        # ИГНОРИРУЕМ SSL ОШИБКИ
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
            
            # Удаляем ненужные элементы
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe']):
                tag.decompose()
            
            # Извлекаем заголовок
            title = self._extract_title(soup, url)
            
            # Извлекаем основной контент
            content = self._extract_main_content(soup)
            
            # Извлекаем контакты
            contacts = self._extract_contacts(content)
            
            # Чистим контент
            clean_content = self._clean_text(content)
            
            return {
                "url": url,
                "title": title,
                "content": clean_content[:3000],  # Ограничиваем объем
                "contacts": contacts,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {url}: {e}")
            return {"url": url, "content": "", "title": "Ошибка парсинга", "error": str(e)}
    
    def _extract_title(self, soup, url: str) -> str:
        """Извлекает заголовок"""
        # Пробуем разные селекторы
        selectors = [
            'h1',
            'title',
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            '.title',
            '.page-title',
            '.article-title'
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
        
        # Если не нашли, берем из URL
        return url.split('//')[-1].split('/')[0].replace('www.', '').capitalize()
    
    def _extract_main_content(self, soup) -> str:
        """Извлекает основной контент"""
        # Ищем основные текстовые контейнеры
        content_selectors = [
            'main',
            'article',
            '.content',
            '.article-content',
            '.post-content',
            '#content',
            '.text',
            '.description'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                texts = [elem.get_text().strip() for elem in elements]
                combined = ' '.join(texts)
                if len(combined) > 100:
                    return combined
        
        # Если не нашли структурированный контент, берем все параграфы
        paragraphs = soup.find_all('p')
        texts = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
        return ' '.join(texts[:15])  # Берем первые 15 параграфов
    
    def _extract_contacts(self, text: str) -> Dict[str, str]:
        """Извлекает контакты из текста"""
        contacts = {
            "address": self._find_pattern(text, r'ул\.?\s+[\w\s\d\-]+,\s*\d+|[А-Яа-я][^,\n]{10,50},\s*\d+'),
            "phone": self._find_pattern(text, r'\+7\s?\(?\d{3}\)?\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}|8\s?\(?\d{3}\)?\s?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'),
            "email": self._find_pattern(text, r'[\w\.-]+@[\w\.-]+\.\w+'),
            "hours": self._find_pattern(text, r'[Пп]н\.?-[Вв]с\.?\s*\d{1,2}:\d{2}-\d{1,2}:\d{2}|\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}')
        }
        
        return {k: v if v else "Не указано" for k, v in contacts.items()}
    
    def _find_pattern(self, text: str, pattern: str) -> str:
        """Ищет паттерн в тексте"""
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    def _clean_text(self, text: str) -> str:
        """Очищает текст от лишних пробелов и символов"""
        # Убираем множественные пробелы и переносы
        text = re.sub(r'\s+', ' ', text)
        # Убираем спецсимволы, но оставляем пунктуацию
        text = re.sub(r'[^\w\s.,!?;:()-]', '', text)
        return text.strip()

class LLMService:
    def __init__(self):
        self.client = Mistral(api_key=config.MISTRAL_API_KEY)
        self.cache = CacheService()
        self.url_database = config.URL_DATABASE
    
    def analyze_preferences(self, text: str) -> Dict[str, Any]:
        """Анализирует предпочтения и возвращает категории"""
        cache_key = self.cache.get_cache_key("pref", text)
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # УСИЛЕННЫЙ ПРОМПТ ДЛЯ JSON
        prompt = f"""Ты должен вернуть ТОЛЬКО JSON без каких-либо пояснений.

Анализируй предпочтения пользователя: "{text}"

Определи категории мест отдыха из этого списка: {', '.join(config.CATEGORIES)}

Ты ДОЛЖЕН вернуть ТОЛЬКО JSON в точном формате:
{{
    "categories": ["категория1", "категория2"],
    "explanation": "короткое объяснение выбора"
}}

ВАЖНО: Только JSON, без других текстов.
"""
        
        try:
            response = self.client.chat.complete(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Ты всегда возвращаешь только валидный JSON. Никакого другого текста."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Убираем возможные обратные кавычки
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Парсим JSON
            result = json.loads(response_text)
            
            # Проверяем структуру
            if "categories" not in result:
                result["categories"] = []
            if "explanation" not in result:
                result["explanation"] = "Определено автоматически"
            
            self.cache.set(cache_key, result, ttl=1800)
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа предпочтений: {e}")
            # Используем fallback
            return self._fallback_category_detection(text)
    
    def _fallback_category_detection(self, text: str) -> Dict[str, Any]:
        """Определение категорий по ключевым словам (резервный метод)"""
        text_lower = text.lower()
        categories = []
        
        keyword_mapping = {
            "🏛️ Музеи": ['музей', 'музеи', 'искусств', 'истори', 'экспоз', 'коллекц'],
            "🎨 Искусство/Выставки": ['искусств', 'выставк', 'галере', 'худож', 'арт', 'картин'],
            "🍽️ Рестораны/Кафе": ['ресторан', 'кафе', 'еда', 'кухн', 'обед', 'ужин', 'завтрак'],
            "☕ Кофейни": ['кофе', 'кофейн', 'латте', 'капучин', 'эспрессо'],
            "🏞️ Парки/Прогулки": ['парк', 'прогул', 'сквер', 'алле', 'отдых', 'природ'],
            "🎭 Театры/Концерты": ['театр', 'концерт', 'спектакл', 'опер', 'балет'],
            "🎳 Развлечения": ['кино', 'боулинг', 'квест', 'аттракцион', 'развлечен'],
            "🛍️ Шоппинг": ['магазин', 'шоппинг', 'торгов', 'покуп', 'бутик'],
            "🎪 События/Фестивали": ['фестивал', 'событи', 'мероприят', 'праздник'],
            "🍻 Бары/Пабы": ['бар', 'паб', 'пиво', 'коктейл', 'напиток']
        }
        
        for category, keywords in keyword_mapping.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        # Если ничего не нашли, возвращаем популярные категории
        if not categories:
            categories = ["🏛️ Музеи", "🍽️ Рестораны/Кафе", "🏞️ Парки/Прогулки"]
        
        return {
            "categories": categories[:3],  # Не больше 3 категорий
            "explanation": f"Определено по ключевым словам: {', '.join(categories[:3])}"
        }
    
    async def get_recommendations(self, categories: List[str]) -> str:
        """Получает рекомендации на основе категорий"""
        cache_key = self.cache.get_cache_key("rec", str(categories))
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 1. Собираем ссылки по категориям
        urls_to_parse = []
        for category in categories:
            if category in self.url_database:
                urls_to_parse.extend(self.url_database[category][:3])  # Берем по 3 ссылки на категорию
        
        if not urls_to_parse:
            return "К сожалению, по выбранным категориям нет информации."
        
        # 2. Парсим сайты асинхронно
        parsed_data = await self._parse_urls_async(urls_to_parse)
        
        # 3. Отправляем в LLM для суммаризации
        recommendations = await self._generate_summary(parsed_data, categories)
        
        # 4. Кэшируем результат
        self.cache.set(cache_key, recommendations, ttl=3600)
        
        return recommendations
    
    async def _parse_urls_async(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Асинхронно парсит список URL"""
        parsed_results = []
        
        async with WebParser() as parser:
            # Загружаем все страницы параллельно
            tasks = [parser.fetch_url(url) for url in urls]
            html_contents = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Парсим полученный контент
            for url, html in zip(urls, html_contents):
                if isinstance(html, Exception):
                    logger.error(f"Ошибка загрузки {url}: {html}")
                    parsed_results.append({
                        "url": url,
                        "content": "",
                        "title": "Ошибка загрузки",
                        "error": str(html)
                    })
                else:
                    parsed = parser.parse_page_content(html, url)
                    parsed_results.append(parsed)
                    
                    # Кэшируем контент
                    if parsed["content"]:
                        self.cache.set_url_content(url, parsed["content"])
        
        # Фильтруем успешные результаты
        successful = [p for p in parsed_results if p.get("content") and len(p["content"]) > 50]
        
        logger.info(f"✅ Успешно распарсено {len(successful)} из {len(urls)} сайтов")
        return successful
    
    async def _generate_summary(self, parsed_data: List[Dict[str, Any]], categories: List[str]) -> str:
        """Генерирует суммаризированный ответ на основе распарсенных данных"""
        if not parsed_data:
            return "Не удалось получить информацию с сайтов. Попробуйте позже."
        
        # Формируем промпт для LLM
        sites_info = []
        for data in parsed_data:
            site_info = f"""
            Сайт: {data['url']}
            Название: {data['title']}
            Контент: {data['content'][:800]}...
            Контакты: {json.dumps(data.get('contacts', {}), ensure_ascii=False)}
            """
            sites_info.append(site_info)
        
        separator = "=" * 50
        prompt = f"""
        Пользователь ищет места в категориях: {', '.join(categories)}
        
        Я проанализировал следующие сайты:
        {separator}
        {separator.join(sites_info)}
        {separator}
        
        На основе этой информации составь КРАТКИЕ рекомендации(до 1500 символов):
        1. Сначала краткий обзор: какие места нашлись, какие интересные
        2. Для каждого места (сайта) дай: 
           - Название и краткое описание
           - Почему стоит посетить (2-3 пункта)
           - Практическая информация (адрес если есть, время работы если есть)
        3. Общие рекомендации: когда лучше посещать, сколько времени планировать
        4. В конце: "На основе анализа сайтов: [список источников]"
        
        Будь КРАТКИМ, конкретным, полезным и дружелюбным. Используй информацию только с указанных сайтов.
        Если информации мало - так и скажи.
        """
        
        try:
            response = self.client.chat.complete(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Ты анализируешь информацию с сайтов и даешь КРАТКИЕ рекомендации по местам отдыха. Будь конкретным и полезным."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            return "Не удалось сформировать рекомендации. Попробуйте позже."
    
    def get_available_categories(self) -> List[str]:
        """Возвращает список категорий, для которых есть ссылки"""
        return list(self.url_database.keys())

class AdminService:
    @staticmethod
    def add_url_to_category(category: str, url: str):
        """Добавляет ссылку в базу (для админа)"""
        if category in config.URL_DATABASE:
            if url not in config.URL_DATABASE[category]:
                config.URL_DATABASE[category].append(url)
                logger.info(f"✅ Добавлена ссылка в категорию {category}: {url}")
                return True
        return False
    
    @staticmethod
    def get_url_stats() -> Dict[str, Any]:
        """Статистика по ссылкам"""
        stats = {}
        for category, urls in config.URL_DATABASE.items():
            stats[category] = len(urls)
        return stats