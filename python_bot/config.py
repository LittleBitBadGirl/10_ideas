import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    DB_URL: str = "sqlite+aiosqlite:///./ideas_bot.db"
    
    # Промпты и настройки
    DAILY_TIME_HOUR: int = 9
    DAILY_TIME_MINUTE: int = 0
    
    DOMAINS: list = [
        'Социальная алхимия', 'Микро-власть', 'Информационное выживание',
        'Временная архитектура', 'Энергетический менеджмент', 'Психологический хакинг',
        'Знаниевая инженерия', 'Контекстное программирование', 'Нарративный контроль',
        'Метаигровое мышление', 'Эмоциональный джиу-джитсу', 'Туманная навигация',
        'Конфликтная хореография', 'Племенная дипломатия', 'Калибровка интуиции',
        'Стратегическое невежество', 'Селективная прозрачность', 'Опционное мышление',
        'Латеральные прыжки', 'Разведка боем'
    ]

settings = Settings()
