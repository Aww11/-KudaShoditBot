from database import Session, User

session = Session()
user = User(
    telegram_id="1692870705",
    role="admin"
)
session.add(user)
session.commit()
session.close()