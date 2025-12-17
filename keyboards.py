from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    """Основная клавиатура"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Рекомендации")],
            [KeyboardButton(text="📋 Категории")],
            [KeyboardButton(text="🆘 Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_admin_keyboard():
    """Клавиатура администратора"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔗 Добавить ссылку")],
            [KeyboardButton(text="🔄 Обновить кэш")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard