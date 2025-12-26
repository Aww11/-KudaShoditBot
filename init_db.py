import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db

if __name__ == "__main__":
    print("Инициализация базы данных...")
    init_db()
    print("\n✅ База данных создана!")
    print("\nЗапустите create_admin.py для создания администратора")