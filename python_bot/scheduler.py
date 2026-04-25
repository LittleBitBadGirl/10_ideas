import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .config import settings
from .database import async_session
from .models import User, IdeaHistory
from .utils import generate_daily_idea
from sqlalchemy import select
from datetime import datetime

async def daily_broadcast():
    from .bot import bot # Избегаем кругового импорта
    
    async with async_session() as session:
        # 1. Получаем историю для промпта
        history_res = await session.execute(
            select(IdeaHistory.prompt_text).distinct().order_by(IdeaHistory.id.desc()).limit(30)
        )
        history_texts = [r[0] for r in history_res.all()]
        
        # 2. Генерируем новую идею
        new_idea = await generate_daily_idea(session, history_texts)
        
        # 3. Получаем всех активных пользователей
        users_res = await session.execute(
            select(User).where(User.status == 'active')
        )
        users = users_res.scalars().all()
        
        for user in users:
            try:
                # Отправляем сообщение
                await bot.send_message(user.chat_id, f"💡 Твоё задание на сегодня:\n\n**{new_idea}**\n\nПришли 10 идей в ответ на это сообщение!")
                
                # Создаем запись в истории
                new_hist = IdeaHistory(
                    user_id=user.id,
                    prompt_text=new_idea,
                    status='pending'
                )
                session.add(new_hist)
            except Exception as e:
                logging.error(f"Failed to send daily idea to {user.chat_id}: {e}")
        
        await session.commit()

async def weekly_stats_broadcast():
    from .bot import bot
    # Здесь логика еженедельной статистики (аналог n8n Flow аналитика)
    # Сократим для примера, можно расширить
    async with async_session() as session:
        users_res = await session.execute(select(User).where(User.status == 'active'))
        for user in users_res.scalars().all():
            stats_text = (
                f"📊 Твоя статистика за неделю:\n"
                f"🔥 Текущая серия: {user.streak_current} дней\n"
                f"🏆 Рекорд: {user.streak_record} дней\n"
                f"✅ Всего выполнено: {user.total_completed} заданий\n"
                f"📝 Ср. количество слов: {user.avg_word_count:.1f}"
            )
            try:
                await bot.send_message(user.chat_id, stats_text)
            except:
                pass

def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Ежедневно в 9:00
    scheduler.add_job(
        daily_broadcast,
        CronTrigger(hour=settings.DAILY_TIME_HOUR, minute=settings.DAILY_TIME_MINUTE)
    )
    
    # Еженедельно (воскресенье, 20:00)
    scheduler.add_job(
        weekly_stats_broadcast,
        CronTrigger(day_of_week='sun', hour=20, minute=0)
    )
    
    return scheduler
