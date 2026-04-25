from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    status = Column(String, default='active')  # active, stopped
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_activity_date = Column(DateTime)
    
    streak_current = Column(Integer, default=0)
    streak_record = Column(Integer, default=0)
    total_completed = Column(Integer, default=0)
    avg_word_count = Column(Float, default=0.0)

    ideas = relationship("IdeaHistory", back_populates="user")

class IdeaHistory(Base):
    __tablename__ = 'ideas_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    prompt_text = Column(String, nullable=False)
    user_answer = Column(String)
    status = Column(String, default='pending')  # pending, done
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="ideas")

class IdeaBank(Base):
    __tablename__ = 'idea_bank'
    
    id = Column(Integer, primary_key=True)
    prompt_text = Column(String, unique=True, nullable=False)
    is_used = Column(Boolean, default=False)
    domain = Column(String)
