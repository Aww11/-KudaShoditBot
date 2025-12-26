from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseLLMClient(ABC):
    """Абстрактный клиент для работы с LLM"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Получение ответа от LLM"""
        pass
    
    @abstractmethod
    def analyze_preferences(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """Анализ предпочтений пользователя"""
        pass
    
    @abstractmethod
    def generate_recommendations(self, parsed_data: List[Dict[str, Any]], categories: List[str]) -> str:
        """Генерация рекомендаций"""
        pass