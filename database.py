from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from sqlalchemy import ForeignKey

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    role = Column(String(20), default='user')  # user, admin
    preferences = Column(Text, default='[]')
    created_at = Column(DateTime, default=datetime.utcnow)

class Place(Base):
    __tablename__ = 'places'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    address = Column(String(300))
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    place_id = Column(Integer, ForeignKey('places.id'))
    text = Column(Text)
    rating = Column(Integer)
    is_moderated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Создаем БД
engine = create_engine('sqlite:///bot.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)