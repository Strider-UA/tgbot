import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq
from telethon import TelegramClient
from telethon.tl.types import PeerChannel

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
API_ID = int(os.environ.get("api_id"))
API_HASH = os.environ.get("api_hash")
PHONE = os.environ.get("PHONE")
ADMIN_ID = os.environ.get("ADMIN_ID")

client_groq = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Telethon клиент
tg_client = TelegramClient("session", API_ID, API_HASH)

chat_histories = {}
group_messages = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    history_key = f"{message.from_user.id}_{message.chat.id}"
    chat_histories[history_key] = []
    await message.answer("Привет! Задай мне любой вопрос 🤖")

@dp.message(Command("reset"))
async def reset(message: types.Message):
    history_key = f"{message.from_user.id}_{message.chat.id}"
    chat_histories[history_key] = []
    await message.answer("История очищена! 🔄")

@dp.message(Command("analyze"))
async def analyze(message: types.Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    await message.answer("⏳ Читаю историю чата, подожди...")

    try:
        # Читаем историю через Telethon
        messages = []
        async with tg_client:
            async for msg in tg_client.iter_messages(message.chat.id, limit=200):
                if msg.text:
                    sender = getattr(msg.sender, "first_name", "Аноним") or "Аноним"
                    messages.append(f"{sender}: {msg.text}")

        messages.reverse()  # от старых к новым
        conversation = "\n".join(messages)

        # Отправляем в ИИ
        response = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Ты анализируешь переписку в групповом чате. Дай подробный анализ: о чём говорят, какое настроение, есть ли конфликты, важные темы, выводы."
                },
                {
                    "role": "user",
                    "content": f"Вот последние сообщения из группы '{message.chat.title}':\n\n{conversation}\n\nПроанализируй."
                }
            ]
        )
        analysis = response.choices[0].message.content

        # Отправляем результат
        await message.answer(f"📊 Анализ:\n\n{analysis}")

        # Отправляем в личку администратору если задан ADMIN_ID
        if ADMIN_ID:
            await bot.send_message(
                chat_id=int(ADMIN_ID),
                text=f"📊 Анализ группы *{message.chat.title}*:\n\n{analysis}",
                parse_mode="Markdown"
            )

    except Exception as e:
        print("ERROR:", e)
        await message.answer(f"Ошибка: {e}")

@dp.message()
async def ai_chat(message: types.Message):
    if not message.text:
        return

    is_private = message.chat.type == "private"
    bot_info = await bot.get_me()
    is_mentioned = f"@{bot_info.username}" in message.text

    if not is_private:
        chat_id = message.chat.id
        if chat_id not in group_messages:
            group_messages[chat_id] = []
        sender = message.from_user.first_name or "Аноним"
        group_messages[chat_id].append(f"{sender}: {message.text}")
        if len(group_messages[chat_id]) > 50:
            group_messages[chat_id].pop(0)
        if not is_mentioned:
            return
        user_text = message.text.replace(f"@{bot_info.username}", "").strip()
        if not user_text:
            user_text = "Привет! Чем могу помочь?"
    else:
        user_text = message.text

    history_key = f"{message.from_user.id}_{message.chat.id}"
    if history_key not in chat_histories:
        chat_histories[history_key] = []

    chat_histories[history_key].append({
        "role": "user",
        "content": user_text
    })

    try:
        response = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_histories[history_key]
        )
        answer = response.choices[0].message.content
        chat_histories[history_key].append({
            "role": "assistant",
            "content": answer
        })
        await message.answer(answer)
    except Exception as e:
        print("ERROR:", e)
        await message.answer(f"Ошибка: {e}")

async def main():
    # Запускаем Telethon авторизацию
    await tg_client.start(phone=PHONE)
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
