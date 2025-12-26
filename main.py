from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.methods import DeleteWebhook
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging

from config import config
from services import LLMService, AdminService
from keyboards import get_main_keyboard, get_admin_keyboard
from prompts import prompts
from database import Session, User, Place, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

llm_service = LLMService()

class UserState(StatesGroup):
    waiting_preferences = State()

class AdminState(StatesGroup):
    waiting_url = State()
    waiting_category = State()

def split_long_message(text: str, max_length: int = 4000) -> list:
    """Разделяет длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 2 > max_length:
            if current_part:
                parts.append(current_part.strip())
            current_part = paragraph
        else:
            if current_part:
                current_part += '\n\n'
            current_part += paragraph
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Начало работы"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not user:
            user = User(
                telegram_id=str(message.from_user.id),
                username=message.from_user.username
            )
            session.add(user)
            session.commit()
    
    await message.answer(
        prompts.MESSAGES["welcome"],
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🎯 Рекомендации")
async def ask_for_preferences(message: Message, state: FSMContext):
    """Запрос предпочтений"""
    await message.answer(
        prompts.MESSAGES["ask_preferences"],
        parse_mode="Markdown"
    )
    await state.set_state(UserState.waiting_preferences)

@dp.message(F.text == "📋 Категории")
async def show_categories_button(message: Message):
    """Показ категорий"""
    categories = llm_service.get_available_categories()
    
    categories_text = "📋 *Доступные категории:*\n\n"
    for category in categories:
        urls_count = len(config.URL_DATABASE.get(category, []))
        categories_text += f"• {category} ({urls_count} источников)\n"
    
    categories_text += "\n*Выберите '🎯 Рекомендации' и опишите, что вас интересует!*"
    
    await message.answer(categories_text, parse_mode="Markdown")

@dp.message(F.text == "🆘 Помощь")
async def show_help_button(message: Message):
    """Помощь"""
    help_text = """*📖 Помощь по использованию бота*

*Как получить рекомендации:*
1. Нажмите "🎯 Рекомендации"
2. Опишите свои предпочтения
3. Бот проанализирует сайты
4. Получите рекомендации

*Примеры запросов:*
• "Хочу сходить в музей"
• "Ищу хороший ресторан"
• "Куда сходить на выходные?"
• "Интересуюсь искусством"

*Команды:*
/start - начать диалог
/help - помощь  
/categories - список категорий
/stats - статистика
"""
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(UserState.waiting_preferences)
async def process_preferences(message: Message, state: FSMContext):
    """Обработка предпочтений"""
    processing_msg = await message.answer(prompts.MESSAGES["processing"], parse_mode="Markdown")
    
    try:
        analysis = llm_service.analyze_preferences(message.text)
        categories = analysis.get("categories", [])
        
        if not categories:
            await processing_msg.delete()
            await message.answer(prompts.MESSAGES["no_categories"], parse_mode="Markdown")
            await state.clear()
            return
        
        explanation_text = analysis.get('explanation', '')
        
        await message.answer(
            f"✅ *Я понял, что вам интересно:*\n\n"
            f"{explanation_text}\n\n"
            f"🔍 *Ищу информацию по категориям:*\n"
            f"{chr(10).join(['• ' + cat for cat in categories])}",
            parse_mode="Markdown"
        )
        
        recommendations = await llm_service.get_recommendations(categories)
        
        await processing_msg.delete()
        
        if recommendations:
            full_response = f"🎯 *Вот что я нашел:*\n\n{recommendations}"
            message_parts = split_long_message(full_response)
            
            for part in message_parts:
                await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer("😔 *Не удалось найти подходящие места.*", parse_mode="Markdown")
        
        await message.answer(
            "🔄 *Хотите уточнить критерии?*\nПросто нажмите '🎯 Рекомендации'",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await message.answer(prompts.MESSAGES["error"], parse_mode="Markdown")
    
    await state.clear()

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    await show_help_button(message)

@dp.message(Command("categories"))
async def cmd_categories(message: Message):
    """Команда списка категорий"""
    await show_categories_button(message)

@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Панель администратора"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not user or user.role != 'admin':
            await message.answer("⛔ У вас нет прав администратора.", reply_markup=get_main_keyboard())
            return
    
    admin_text = """*⚙️ Панель администратора*

*Статистика:*"""
    
    stats = AdminService.get_url_stats()
    total_sites = 0
    
    for category, count in stats.items():
        admin_text += f"\n• {category}: {count} ссылок"
        total_sites += count
    
    admin_text += f"\n\n*Итого:* {total_sites} ссылок\n\nВыберите действие:"
    
    await message.answer(admin_text, parse_mode="Markdown", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.message(F.text == "📊 Статистика")
async def show_admin_stats(message: Message):
    """Статистика для админа"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not user or user.role != 'admin':
            return
    
    stats = AdminService.get_url_stats()
    total_users = session.query(User).count()
    total_places = session.query(Place).count()
    
    stats_text = f"""*📊 Детальная статистика:*

*Пользователи:*
• Всего: {total_users}
• Админы: {session.query(User).filter_by(role='admin').count()}

*Места:*
• Всего: {total_places}
• Активных: {session.query(Place).filter_by(is_active=True).count()}

*Источники по категориям:*"""
    
    for category, count in stats.items():
        stats_text += f"\n• {category}: {count}"
    
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message(F.text == "🔗 Добавить ссылку")
async def add_url_start(message: Message, state: FSMContext):
    """Начало добавления ссылки"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not user or user.role != 'admin':
            return
    
    categories = list(config.URL_DATABASE.keys())
    categories_text = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(categories)])
    
    await message.answer(
        f"*Выберите категорию для добавления ссылки:*\n\n{categories_text}\n\n"
        f"Отправьте номер категории (1-{len(categories)})",
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.waiting_category)

@dp.message(AdminState.waiting_category)
async def add_url_category(message: Message, state: FSMContext):
    """Обработка выбора категории"""
    try:
        index = int(message.text.strip()) - 1
        categories = list(config.URL_DATABASE.keys())
        
        if 0 <= index < len(categories):
            category = categories[index]
            await state.update_data(category=category)
            await message.answer(
                f"*Категория: {category}*\n\n"
                f"Теперь отправьте URL сайта (например: https://example.com)",
                parse_mode="Markdown"
            )
            await state.set_state(AdminState.waiting_url)
        else:
            await message.answer("❌ Неверный номер категории. Попробуйте снова.")
    except ValueError:
        await message.answer("❌ Отправьте номер категории.")

@dp.message(AdminState.waiting_url)
async def add_url_finish(message: Message, state: FSMContext):
    """Обработка URL"""
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ URL должен начинаться с http:// или https://")
        return
    
    data = await state.get_data()
    category = data.get('category')
    
    if AdminService.add_url_to_category(category, url):
        await message.answer(f"✅ Ссылка добавлена в категорию '{category}'")
    else:
        await message.answer("❌ Ошибка добавления ссылки")
    
    await state.clear()
    await admin_panel(message, state)

@dp.message(F.text == "🔄 Обновить кэш")
async def clear_cache(message: Message):
    """Очистка кэша Redis"""
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not user or user.role != 'admin':
            return
    
    from services import CacheService
    cache = CacheService()
    
    if cache.redis:
        cache.redis.flushall()
        await message.answer("✅ Кэш Redis очищен")
    else:
        await message.answer("⚠️ Redis не подключен")

@dp.message(F.text == "◀️ Назад")
async def back_to_main(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(Command("stats"))
async def show_stats(message: Message):
    """Статистика бота"""
    stats = AdminService.get_url_stats()
    total_categories = len(stats)
    total_sites = sum(stats.values())
    
    stats_text = f"""📊 *Статистика бота:*

*Категории и источники:*"""
    
    for category, count in stats.items():
        stats_text += f"\n• {category}: {count} сайтов"
    
    stats_text += f"""

*Итого:*
• Категорий: {total_categories}
• Всего сайтов: {total_sites}
• Модель LLM: {config.LLM_MODEL}
"""
    
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message()
async def handle_other_messages(message: Message):
    """Обработчик остальных сообщений"""
    if message.text and not message.text.startswith('/'):
        await message.answer(
            "🤖 *Нажмите '🎯 Рекомендации' для получения рекомендаций.*\n"
            "*Или используйте:*\n"
            "• /help - помощь\n"
            "• /categories - список категорий",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def main():
    """Основная функция запуска бота"""
    await bot(DeleteWebhook(drop_pending_updates=True))
    
    print("=" * 50)
    print("🤖 *Бот рекомендаций мест отдыха*")
    print("=" * 50)
    
    init_db()
    
    stats = AdminService.get_url_stats()
    total_categories = len(stats)
    total_sites = sum(stats.values())
    
    print(f"📊 Загружено категорий: {total_categories}")
    print(f"🔗 Всего ссылок в базе: {total_sites}")
    print(f"🧠 Модель LLM: {config.LLM_MODEL}")
    print(f"🗄️  База данных: {config.DATABASE_URL}")
    print("=" * 50)
    print("✅ Бот запущен и готов к работе!")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")