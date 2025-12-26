import re
from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    """Проверка валидности URL"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def is_valid_telegram_id(telegram_id: str) -> bool:
    """Проверка валидности Telegram ID"""
    return telegram_id.isdigit() and len(telegram_id) >= 5

def is_valid_category(category: str, available_categories: list) -> bool:
    """Проверка, что категория существует"""
    return category in available_categories

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Очистка текста от потенциально опасных символов"""
    if not text:
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем слишком длинные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Обрезаем длину
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()