import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Session, User

def create_admin_user():
    """Создание администратора через интерактивный ввод"""
    print("=" * 40)
    print("Создание администратора")
    print("=" * 40)
    
    try:
        telegram_id = input("Введите Telegram ID: ").strip()
        username = input("Введите username (необязательно): ").strip()
        
        if not telegram_id:
            print("❌ Telegram ID обязателен!")
            return
        
        session = Session()
        
        # Проверяем существующего пользователя
        existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if existing_user:
            print(f"⚠️ Пользователь {telegram_id} уже существует")
            update = input("Сделать администратором? (y/n): ").lower()
            if update == 'y':
                existing_user.role = 'admin'
                session.commit()
                print(f"✅ Пользователь теперь администратор")
            else:
                print("❌ Отменено")
        else:
            # Создаем нового
            user = User(
                telegram_id=telegram_id,
                username=username or None,
                role='admin'
            )
            session.add(user)
            session.commit()
            print(f"✅ Создан администратор ID: {telegram_id}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    create_admin_user()