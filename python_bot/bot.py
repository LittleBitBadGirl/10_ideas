import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from datetime import datetime

import random
from .config import settings
from .database import init_db, async_session
from .models import User, IdeaHistory, IdeaBank
from .scheduler import setup_scheduler
from .utils import calculate_streak, count_ideas, REJECT_PHRASES
from sqlalchemy import select, update

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.chat_id == message.chat.id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                chat_id=message.chat.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            session.add(user)
            await session.commit()
            
        welcome_text = (
            "Привет! 👋 Добро пожаловать в тренажёр креативности «10 идей»!\n\n"
            "🧠 Каждое утро в 9:00 я буду присылать тебе тему.\n"
            "Твоя задача — прислать 10 идей в ответ.\n\n"
            "Первое задание придет завтра в 9:00! 🚀"
        )
        await message.answer(welcome_text)

@dp.message(F.text, F.reply_to_message)
async def handle_answer(message: types.Message):
    """Обработка ответа на задание (через Reply)."""
    async with async_session() as session:
        # 0. Проверяем количество идей
        count = count_ideas(message.text)
        if count < 10:
            await message.answer(f"⚠️ {random.choice(REJECT_PHRASES)}\n(Я насчитал всего {count} из 10, но так и быть — сегодня засчитаю...)")
        
        # 1. Находим пользователя
        res = await session.execute(select(User).where(User.chat_id == message.chat.id))
        user = res.scalar_one_or_none()
        if not user: return

        # 2. Находим активное задание (по тексту сообщения на которое ответили)
        prompt_text = message.reply_to_message.text.split("\n\n")[-1] # Упрощенно
        hist_res = await session.execute(
            select(IdeaHistory).where(
                IdeaHistory.user_id == user.id,
                IdeaHistory.status == 'pending'
            ).order_by(IdeaHistory.id.desc()).limit(1)
        )
        idea_hist = hist_res.scalar_one_or_none()
        
        if not idea_hist:
            await message.answer("Похоже, это не ответ на актуальное задание или ты уже на него ответил.")
            return

        # 3. Обновляем статистику и стрик
        streak_action = calculate_streak(user.last_activity_date)
        if streak_action == "increment":
            user.streak_current += 1
        elif streak_action == "reset":
            user.streak_current = 1
        
        if user.streak_current > user.streak_record:
            user.streak_record = user.streak_current
            
        # Считаем среднее кол-во слов
        words = len(message.text.split())
        user.avg_word_count = (user.avg_word_count * user.total_completed + words) / (user.total_completed + 1)
        
        user.total_completed += 1
        user.last_activity_date = datetime.utcnow()
        
        # Обновляем историю задания
        idea_hist.user_answer = message.text
        idea_hist.status = 'done'
        
        await session.commit()
        await message.answer("Записал! ✓ Увидимся завтра 👋")

@dp.edited_message(F.text)
async def handle_edit(edited_message: types.Message):
    """Обработка редактирования ответа."""
    async with async_session() as session:
        res = await session.execute(select(User).where(User.chat_id == edited_message.chat.id))
        user = res.scalar_one_or_none()
        if not user: return

        # Находим последнюю выполненную идею сегодня
        hist_res = await session.execute(
            select(IdeaHistory).where(
                IdeaHistory.user_id == user.id,
                IdeaHistory.status == 'done'
            ).order_by(IdeaHistory.id.desc()).limit(1)
        )
        idea_hist = hist_res.scalar_one_or_none()
        
        if idea_hist:
            idea_hist.user_answer = edited_message.text
            await session.commit()
            await edited_message.answer("Спасибо за уточнение, обновил ответ! ✍️")

@dp.message(Command("admin_load_bank"))
async def load_bank(message: types.Message):
    if message.chat.id != settings.ADMIN_ID: return
    
    # Пример: загрузка из текста сообщения (каждая строка - новая идея)
    ideas = message.text.replace("/admin_load_bank", "").strip().split("\n")
    async with async_session() as session:
        for idea_text in ideas:
            if not idea_text.strip(): continue
            session.add(IdeaBank(prompt_text=idea_text.strip()))
        await session.commit()
    await message.answer(f"Загружено {len(ideas)} идей в банк.")

async def main():
    await init_db()
    
    scheduler = setup_scheduler()
    scheduler.start()
    
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
