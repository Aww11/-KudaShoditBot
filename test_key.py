import os
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

key = os.getenv('API_KEY')
print(f"Ключ загружен: {'ДА' if key else 'НЕТ'}")
print(f"Длина ключа: {len(key) if key else 0}")
print(f"Начинается с 'mistral-': {key.startswith('mistral-') if key else False}")

# Попробуем вызвать API
try:
    client = Mistral(api_key=key)
    response = client.chat.complete(
        model="mistral-tiny",
        messages=[{"role": "user", "content": "Привет"}],
        max_tokens=10
    )
    print("✅ API ключ РАБОТАЕТ!")
except Exception as e:
    print(f"❌ Ошибка API: {e}")