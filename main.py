from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.methods import DeleteWebhook
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging
import json
import re

from config import config
from services import LLMService, AdminService
from keyboards import get_main_keyboard, get_admin_keyboard

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

llm_service = LLMService()

class UserState(StatesGroup):
    waiting_preferences = State()

def split_long_message(text: str, max_length: int = 4000) -> list:
    """Разделяет длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разделяем по абзацам
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
    welcome_text = f"""
👋 *Привет! Я помогу найти интересные места для отдыха!*

🎯 *Как это работает:*
1. Нажмите "🎯 Рекомендации"
2. Расскажите, что любите (например: "люблю музеи и искусство")
3. Я проанализирую официальные сайты
4. Вы получите персонализированные рекомендации

📋 *Доступные категории:*
{chr(10).join(['• ' + cat for cat in llm_service.get_available_categories()])}

*Начнем? Нажмите "🎯 Рекомендации"!*
"""
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(F.text == "🎯 Рекомендации")
async def ask_for_preferences(message: Message, state: FSMContext):
    """Обработчик кнопки Рекомендации"""
    await message.answer(
        "✨ *Расскажите, что вы любите делать в свободное время?*\n\n"
        "*Например:*\n"
        "• Люблю ходить в музеи и на выставки\n"
        "• Ищу интересные рестораны\n" 
        "• Хочу погулять в парках\n"
        "• Интересуюсь искусством и театром\n"
        "• Ищу места для свидания\n"
        "• Хочу куда-то сходить с детьми",
        parse_mode="Markdown"
    )
    await state.set_state(UserState.waiting_preferences)

@dp.message(F.text == "📋 Категории")
async def show_categories_button(message: Message):
    """Обработчик кнопки Категории"""
    categories = llm_service.get_available_categories()
    
    categories_text = "📋 *Доступные категории:*\n\n"
    for category in categories:
        urls_count = len(config.URL_DATABASE.get(category, []))
        categories_text += f"• {category} ({urls_count} источников)\n"
    
    categories_text += "\n*Выберите '🎯 Рекомендации' и опишите, что вас интересует!*"
    
    await message.answer(categories_text, parse_mode="Markdown")

@dp.message(F.text == "🆘 Помощь")
async def show_help_button(message: Message):
    """Обработчик кнопки Помощь"""
    help_text = """
*📖 Помощь по использованию бота*

*Как получить рекомендации:*
1. Нажмите "🎯 Рекомендации"
2. Опишите свои предпочтения
3. Бот проанализирует официальные сайты
4. Получите персонализированные рекомендации

*Примеры запросов:*
• "Хочу сходить в музей"
• "Ищу хороший ресторан"
• "Куда сходить на выходные?"
• "Интересуюсь современным искусством"
• "Где погулять в Москве?"
• "Ищу романтическое место для свидания"
• "Куда сходить с детьми?"

*📊 Источники информации:*
Бот анализирует официальные сайты музеев, театров, ресторанов и других заведений.

*⚙️ Команды:*
/start - начать диалог
/help - эта справка  
/categories - список категорий
"""
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(UserState.waiting_preferences)
async def process_preferences(message: Message, state: FSMContext):
    """Обработка предпочтений и генерация рекомендаций"""
    user_preferences = message.text
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("⏳ *Обрабатываю ваш запрос...*", parse_mode="Markdown")
    
    try:
        # 1. Анализируем предпочтения
        await message.answer("🤔 *Анализирую ваши предпочтения...*", parse_mode="Markdown")
        analysis = llm_service.analyze_preferences(user_preferences)
        categories = analysis.get("categories", [])
        
        if not categories:
            await processing_msg.delete()
            await message.answer(
                "🤷 *Не удалось определить категории.*\n\n"
                "*Попробуйте описать подробнее:*\n"
                "• 'Интересуюсь современным искусством'\n"
                "• 'Хочу сходить в хороший ресторан'\n"
                "• 'Ищу места для прогулок в парках'",
                parse_mode="Markdown"
            )
            await state.clear()
            return
        
        explanation_text = analysis.get('explanation', '')
        
        # 2. Показываем определенные категории
        await message.answer(
            f"✅ *Отлично! Я понял, что вам интересно:*\n\n"
            f"{explanation_text}\n\n"
            f"🔍 *Ищу информацию по категориям:*\n"
            f"{chr(10).join(['• ' + cat for cat in categories])}\n\n"
            f"⏱️ *Это займет около 10-15 секунд...*",
            parse_mode="Markdown"
        )
        
        # 3. Получаем рекомендации (асинхронно парсим сайты)
        recommendations = await llm_service.get_recommendations(categories)
        
        # 4. Удаляем сообщение "Обрабатываю..."
        await processing_msg.delete()
        
        # 5. Разделяем и отправляем результат
        if recommendations:
            # Добавляем заголовок
            full_response = f"🎯 *Вот что я нашел для вас:*\n\n{recommendations}"
            
            # Разделяем длинное сообщение
            message_parts = split_long_message(full_response)
            
            # Отправляем первую часть
            await message.answer(message_parts[0], parse_mode="Markdown")
            
            # Отправляем остальные части
            for part in message_parts[1:]:
                await message.answer(part, parse_mode="Markdown")
                
            # 6. Показываем статистику
            stats = AdminService.get_url_stats()
            analyzed_sites = sum(stats.get(cat, 0) for cat in categories if cat in stats)
            
            await message.answer(
                f"📊 *Статистика запроса:*\n"
                f"• Проанализировано категорий: {len(categories)}\n"
                f"• Использовано источников: {analyzed_sites}\n\n"
                f"💡 *Совет:* Сохраните понравившиеся варианты!",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "😔 *Не удалось найти подходящие места.*\n\n"
                "*Попробуйте:*\n"
                "• Изменить критерии поиска\n"
                "• Описать предпочтения иначе\n"
                "• Выбрать другие категории",
                parse_mode="Markdown"
            )
        
        # 7. Предлагаем уточнить
        await message.answer(
            "🔄 *Хотите уточнить критерии или посмотреть другие категории?*\n\n"
            "Просто нажмите '🎯 Рекомендации' и опишите, что еще интересует!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки предпочтений: {e}")
        
        try:
            await processing_msg.delete()
        except:
            pass
        
        await message.answer(
            "❌ *Произошла ошибка при обработке запроса.*\n\n"
            "*Что можно сделать:*\n"
            "• Попробовать позже\n"
            "• Сформулировать запрос иначе\n"
            "• Использовать более простые слова",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
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
async def admin_panel(message: Message):
    """Панель администратора"""
    admin_text = """*⚙️ Панель администратора*

*Статистика по ссылкам:*
"""
    
    stats = AdminService.get_url_stats()
    total_sites = 0
    
    for category, count in stats.items():
        admin_text += f"• {category}: {count} ссылок\n"
        total_sites += count
    
    admin_text += f"\n*Итого:* {total_sites} ссылок в базе\n\n"
    admin_text += """*Команды:*
/add_url - добавить новую ссылку
/update_cache - обновить кэш"""
    
    await message.answer(admin_text, parse_mode="Markdown", reply_markup=get_admin_keyboard())

@dp.message(Command("stats"))
async def show_stats(message: Message):
    """Показывает статистику бота"""
    stats = AdminService.get_url_stats()
    total_categories = len(stats)
    total_sites = sum(stats.values())
    
    stats_text = f"""
📊 *Статистика бота:*

*Категории и источники:*
"""
    
    for category, count in stats.items():
        stats_text += f"• {category}: {count} сайтов\n"
    
    stats_text += f"""
*Итого:*
• Категорий: {total_categories}
• Всего сайтов: {total_sites}
• Модель LLM: {config.LLM_MODEL}

*Бот успешно работает и готов помогать!* 🚀
"""
    
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message()
async def handle_other_messages(message: Message):
    """Обработчик остальных сообщений"""
    # Если пользователь просто написал текст (не команду и не в состоянии)
    if message.text and not message.text.startswith('/'):
        response = await message.answer(
            "🤖 *Я понимаю, что вы написали, но для получения рекомендаций нужно нажать '🎯 Рекомендации'.*\n\n"
            "*Или используйте:*\n"
            "• /help - помощь\n"
            "• /categories - список категорий\n"
            "• /stats - статистика бота",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def main():
    """Основная функция запуска бота"""
    await bot(DeleteWebhook(drop_pending_updates=True))
    
    print("=" * 50)
    print("🤖 *Бот рекомендаций мест отдыха*")
    print("=" * 50)
    
    # Статистика при запуске
    stats = AdminService.get_url_stats()
    total_categories = len(stats)
    total_sites = sum(stats.values())
    
    print(f"📊 Загружено категорий: {total_categories}")
    print(f"🔗 Всего ссылок в базе: {total_sites}")
    print(f"🧠 Модель LLM: {config.LLM_MODEL}")
    print("🌐 Режим: анализ официальных сайтов в реальном времени")
    print("💾 Кэширование: Redis")
    print("=" * 50)
    print("✅ Бот запущен и готов к работе!")
    print("⚠️  Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()