import json
import logging
from mistralai import Mistral
from typing import Dict, Any, List

from base import BaseLLMClient
from config import config
from prompts import prompts

logger = logging.getLogger(__name__)

class MistralClient(BaseLLMClient):
    """Реализация для Mistral AI"""
    
    def __init__(self):
        self.client = Mistral(api_key=config.MISTRAL_API_KEY)
        self.model = config.LLM_MODEL
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Получение ответа от Mistral"""
        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка Mistral API: {e}")
            raise
    
    def analyze_preferences(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """Анализ предпочтений пользователя"""
        prompt = prompts.PREFERENCE_ANALYZER.format(
            user_input=text,
            categories=', '.join(categories)
        )
        
        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты всегда возвращаешь только валидный JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else lines[0]
            
            result = json.loads(response_text)
            
            if "categories" not in result:
                result["categories"] = []
            if "explanation" not in result:
                result["explanation"] = "Определено автоматически"
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа предпочтений: {e}")
            return self._fallback_category_detection(text, categories)
    
    def generate_recommendations(self, parsed_data: List[Dict[str, Any]], categories: List[str]) -> str:
        """Генерация рекомендаций на основе распарсенных данных"""
        if not parsed_data:
            return "Не удалось получить информацию с сайтов."
        
        # Формируем информацию о сайтах
        sites_info = []
        for data in parsed_data:
            site_info = f"\nСайт: {data['url']}\n"
            site_info += f"Название: {data['title']}\n"
            if data.get('content'):
                site_info += f"Контент: {data['content'][:500]}...\n"
            sites_info.append(site_info)
        
        prompt = prompts.RECOMMENDATION_GENERATOR.format(
            categories=', '.join(categories),
            sites_info='\n---\n'.join(sites_info)
        )
        
        try:
            return self.chat_completion(
                messages=[
                    {"role": "system", "content": "Ты даешь рекомендации по местам отдыха."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            return "Не удалось сформировать рекомендации."
    
    def _fallback_category_detection(self, text: str, available_categories: List[str]) -> Dict[str, Any]:
        """Резервный метод определения категорий"""
        text_lower = text.lower()
        categories = []
        
        keyword_mapping = {
            "🏛️ Музеи": ['музей', 'истори', 'экспоз'],
            "🎨 Искусство/Выставки": ['искусств', 'выставк', 'галере', 'арт'],
            "🍽️ Рестораны/Кафе": ['ресторан', 'кафе', 'еда', 'кухн'],
            "☕ Кофейни": ['кофе', 'кофейн'],
            "🏞️ Парки/Прогулки": ['парк', 'прогул', 'сквер'],
            "🎭 Театры/Концерты": ['театр', 'концерт', 'спектакл'],
            "🎳 Развлечения": ['кино', 'боулинг', 'квест'],
            "🛍️ Шоппинг": ['магазин', 'шоппинг', 'торгов'],
            "🎪 События/Фестивали": ['фестивал', 'событи', 'мероприят'],
            "🍻 Бары/Пабы": ['бар', 'паб', 'пиво', 'коктейл']
        }
        
        for category, keywords in keyword_mapping.items():
            if category in available_categories and any(k in text_lower for k in keywords):
                categories.append(category)
        
        if not categories:
            categories = available_categories[:2] if available_categories else []
        
        return {
            "categories": categories[:3],
            "explanation": f"Определено по ключевым словам: {', '.join(categories)}"
        }