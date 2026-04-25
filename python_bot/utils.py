import re
import random
import logging
from anthropic import AsyncAnthropic
from .config import settings
from .models import IdeaBank, IdeaHistory
from sqlalchemy import select, func, update
from datetime import datetime, timedelta

# Набор "пинающих" фраз
REJECT_PHRASES = [
    "Слушай, ты конечно молодец, но недоработочка — тут явно не 10!",
    "Почти дотянул, но мозг еще не вспотел. Давай еще варианты до десятки!",
    "Вижу старание, но Альтучер бы не одобрил. Нужно ровно 10, не халтурь.",
    "Где-то я это видел... а именно — меньше десяти идей. Попробуй еще раз.",
    "Экономим калории? Давай-давай, еще парочку идей и будет зачет.",
    "Хорошее начало, но нам нужно количество! Добивай до 10.",
    "Твой внутренний критик победил на полпути. Выгони его и допиши еще несколько!"
]

def count_ideas(text: str) -> int:
    """Считает количество идей в тексте."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    count = 0
    for line in lines:
        if re.match(r'^(\d+[\.\)]|[\-\*\•])\s*', line) or len(line) > 3:
            count += 1
    return count

client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

async def generate_daily_idea(session, history_texts):
    """
    Генерирует новую идею через Claude Haiku с провокационным тоном.
    """
    history_str = "\n".join([f"- {t}" for t in history_texts[-20:]])
    
    # Список доменов для промпта
    domains_str = "\n".join([f"- {d}" for d in settings.DOMAINS])
    
    system_prompt = f"""Ты — Мастер Социального Хакинга, провокатор и идеолог изворотливости. 
Твоя задача — генерировать задания для упражнения '10 идей', которые заставляют мозг плавиться.

ТОН: 
Дерзкий, циничный, вдохновляющий на нарушение статус-кво. Ты не даешь советов, ты ставишь в неудобные, опасные или азартные ситуации.

БИБЛИОТЕКА ДОМЕНОВ (выбери один для нового задания):
{domains_str}

ПРАВИЛА ИГРЫ:
1. Максимум 15 слов. Краткость — твоя власть.
2. Глаголы-триггеры: выжить, убедить, захватить, стравить, оптимизировать, скрыть, восстановить, перехватить, создать.
3. НИКАКИХ предметов. Только социальные игры, власть, информация и психология.
4. Задание должно быть на грани — реалистичным, но требующим 'грязных' или гениальных приемов.
5. НИКАКИХ ПОВТОРОВ. Если задание похоже на то, что уже было — ты проиграл.

ИСТОРИЯ ОПЕРАЦИЙ (не повторяй это):
{history_str}

Если ты исписался или видишь, что начинаешь повторяться — ответь словом 'FALLBACK'.
В остальном — выдай только одну строку текста задания. Никаких вступлений, кавычек и мусора."""

    try:
        response = await client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=150,
            temperature=0.9, # Чуть больше хаоса для креативности
            system=system_prompt,
            messages=[{"role": "user", "content": "Выдай следующую цель для тренировки."}]
        )
        content = response.content[0].text.strip().replace('"', '')
        
        if content.upper() == 'FALLBACK' or any(h.lower() in content.lower() for h in history_texts[-7:]):
            logging.info("Detected AI fatigue or duplicate. Switching to manual bank.")
            return await get_idea_from_bank(session)
        
        return content
    except Exception as e:
        logging.error(f"Error generating idea with Claude: {e}")
        return await get_idea_from_bank(session)

async def get_idea_from_bank(session):
    """Берет неиспользованную идею из банка."""
    result = await session.execute(
        select(IdeaBank).where(IdeaBank.is_used == False).limit(1)
    )
    idea = result.scalar_one_or_none()
    
    if idea:
        idea.is_used = True
        await session.commit()
        
        count_res = await session.execute(
            select(func.count(IdeaBank.id)).where(IdeaBank.is_used == False)
        )
        remaining = count_res.scalar()
        if remaining <= 10:
            await notify_admin_low_bank(remaining)
            
        return idea.prompt_text
    
    return "Придумай 10 идей, как выжить в офисе, если ты тайно уволился неделю назад."

async def notify_admin_low_bank(remaining):
    from .bot import bot
    try:
        await bot.send_message(settings.ADMIN_ID, f"⚠️ ОПЕРАЦИЯ ПОД УГРОЗОЙ: В банке идей осталось всего {remaining} вариантов! Срочно пополни запасы.")
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")

def calculate_streak(last_activity: datetime):
    if not last_activity:
        return 1
    
    today = datetime.utcnow().date()
    last_date = last_activity.date()
    diff = (today - last_date).days
    
    if diff == 0:
        return None 
    if diff == 1:
        return "increment"
    return "reset"
