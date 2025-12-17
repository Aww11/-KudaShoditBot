import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MISTRAL_API_KEY = os.getenv('API_KEY')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    LLM_MODEL = "mistral-large-latest"
    
    # Категории
    CATEGORIES = [
        "🍽️ Рестораны/Кафе",
        "🎨 Искусство/Выставки", 
        "🎭 Театры/Концерты",
        "🏞️ Парки/Прогулки",
        "🎳 Развлечения",
        "🛍️ Шоппинг",
        "🏛️ Музеи",
        "🎪 События/Фестивали",
        "☕ Кофейни",
        "🍻 Бары/Пабы"
    ]
    
    # База ссылок на реальные сайты (по категориям)
    # Можно расширять сколько угодно
    URL_DATABASE = {
        "🏛️ Музеи": [
            "https://tretyakovgallery.ru",        # Третьяковская галерея
            "https://hermitagemuseum.org",        # Эрмитаж
            "https://www.polymus.ru",             # Политехнический музей
            "https://www.pushkinmuseum.art",      # Музей Пушкина
            "https://www.kreml.ru",               # Музеи Кремля
            "https://www.rusmuseum.ru",           # Русский музей
            "https://moscowmanege.ru",            # Манеж
            "https://www.darwinmuseum.ru",        # Дарвиновский музей
            "https://www.kosmo-museum.ru",        # Музей космонавтики
        ],
        "🎨 Искусство/Выставки": [
            "https://www.garageccc.com",          # Гараж
            "https://www.mmoma.ru",               # ММОМА
            "https://www.arts-museum.ru",         # ГМИИ им. Пушкина
            "https://www.moscowmuseum.ru",        # Музей Москвы
            "https://winzavod.ru",                # Винзавод
            "https://www.newtretiakov.ru",        # Новая Третьяковка
        ],
        "🍽️ Рестораны/Кафе": [
            "https://white-rabbit.ru",            # White Rabbit
            "https://www.turandot-palace.ru",     # Турандот
            "https://shinok.ru",                  # Шинок
            "https://cafepushkin.ru",             # Кафе Пушкинъ
            "https://www.durdom.ru",              # Дуры
            "https://twinsgarden.ru",             # Twins Garden
        ],
        "☕ Кофейни": [
            "https://coffeemania.ru",             # Coffeemania
            "https://surfcoffee.ru",              # Surf Coffee
            "https://double-b.ru",                # Double B
            "https://tccworld.com",               # The Coffee & Cake
        ],
        "🏞️ Парки/Прогулки": [
            "https://park-gorkogo.com",           # Парк Горького
            "https://vdnh.ru",                    # ВДНХ
            "https://moscowzoo.ru",               # Московский зоопарк
            "https://www.sokolniki.com",          # Сокольники
            "https://www.aptekarsky-ogorod.ru",   # Аптекарский огород
            "https://www.mgomz.ru",               # Коломенское
        ],
        "🎭 Театры/Концерты": [
            "https://bolshoi.ru",                 # Большой театр
            "https://mikhailovsky.ru",            # Михайловский театр
            "https://www.mariinsky.ru",           # Мариинский театр
            "https://lenkom.ru",                  # Ленком
            "https://sovremennik.ru",             # Современник
            "https://mdt-dodin.ru",               # МДТ
        ],
        "🎳 Развлечения": [
            "https://moskvarium.ru",              # Москвариум
            "https://planetarium-moscow.ru",      # Планетарий
            "https://www.mosobleirc.ru",          # Океанариум
            "https://www.park-zaryadye.ru",       # Зарядье
            "https://www.cosmoscow.com",          # Космос (ВДНХ)
        ],
        "🎪 События/Фестивали": [
            "https://www.moscowseasons.com",      # Московские сезоны
            "https://www.flower-expo.ru",         # Цветочная выставка
            "https://www.circus.ru",              # Цирк
            "https://www.icefest.ru",             # Фестиваль мороженого
        ]
    }

config = Config()