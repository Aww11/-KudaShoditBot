from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100))
    role = Column(String(20), default='user', nullable=False)
    preferences = Column(Text, default='[]')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"

class Place(Base):
    __tablename__ = 'places'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), index=True)
    address = Column(String(300))
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    source_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    reviews = relationship("Review", back_populates="place", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Place(id={self.id}, name='{self.name}')>"

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    place_id = Column(Integer, ForeignKey('places.id', ondelete='CASCADE'), nullable=False)
    text = Column(Text)
    rating = Column(Integer)
    is_moderated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reviews")
    place = relationship("Place", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(id={self.id})>"

# Используем PostgreSQL из конфига
from config import config
engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(engine)
    print(f"✅ База данных инициализирована: {config.DATABASE_URL}")