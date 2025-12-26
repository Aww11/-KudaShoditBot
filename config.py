import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MISTRAL_API_KEY = os.getenv('API_KEY')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Database
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'recommendations')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
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
    
    # База ссылок на реальные сайты
    URL_DATABASE = {
        "🏛️ Музеи": [
            "https://tretyakovgallery.ru",
            "https://hermitagemuseum.org",
            "https://www.polymus.ru",
            "https://www.pushkinmuseum.art",
            "https://www.kreml.ru",
            "https://www.rusmuseum.ru",
            "https://moscowmanege.ru",
            "https://www.darwinmuseum.ru",
            "https://www.kosmo-museum.ru",
        ],
        "🎨 Искусство/Выставки": [
            "https://www.garageccc.com",
            "https://www.mmoma.ru",
            "https://www.arts-museum.ru",
            "https://www.moscowmuseum.ru",
            "https://winzavod.ru",
            "https://www.newtretiakov.ru",
        ],
        "🍽️ Рестораны/Кафе": [
            "https://white-rabbit.ru",
            "https://www.turandot-palace.ru",
            "https://shinok.ru",
            "https://cafepushkin.ru",
            "https://www.durdom.ru",
            "https://twinsgarden.ru",
        ],
        "☕ Кофейни": [
            "https://coffeemania.ru",
            "https://surfcoffee.ru",
            "https://double-b.ru",
            "https://tccworld.com",
        ],
        "🏞️ Парки/Прогулки": [
            "https://park-gorkogo.com",
            "https://vdnh.ru",
            "https://moscowzoo.ru",
            "https://www.sokolniki.com",
            "https://www.aptekarsky-ogorod.ru",
            "https://www.mgomz.ru",
        ],
        "🎭 Театры/Концерты": [
            "https://bolshoi.ru",
            "https://mikhailovsky.ru",
            "https://www.mariinsky.ru",
            "https://lenkom.ru",
            "https://sovremennik.ru",
            "https://mdt-dodin.ru",
        ],
        "🎳 Развлечения": [
            "https://moskvarium.ru",
            "https://planetarium-moscow.ru",
            "https://www.mosobleirc.ru",
            "https://www.park-zaryadye.ru",
            "https://www.cosmoscow.com",
        ],
        "🎪 События/Фестивали": [
            "https://www.moscowseasons.com",
            "https://www.flower-expo.ru",
            "https://www.circus.ru",
            "https://www.icefest.ru",
        ]
    }

config = Config()