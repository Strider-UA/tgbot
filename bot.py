import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# История диалогов для лички
chat_histories = {}

# Последние сообщения в группах для анализа
group_messages = {}



@dp.message(Command("start"))
async def start(message: types.Message):
    chat_histories[message.from_user.id] = []
    await message.answer("Привет! Задай мне любой вопрос 🤖")

@dp.message(Command("reset"))
async def reset(message: types.Message):
    chat_histories[message.from_user.id] = []
    await message.answer("История очищена! 🔄")

@dp.message(Command("analyze"))
async def analyze(message: types.Message):
    """Команда для анализа последних сообщений в группе"""
    chat_id = message.chat.id

    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    if chat_id not in group_messages or len(group_messages[chat_id]) == 0:
        await message.answer("Пока нет сообщений для анализа.")
        return

    # Собираем последние 20 сообщений
    last_messages = group_messages[chat_id][-20:]
    conversation = "\n".join(last_messages)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Ты анализируешь переписку в групповом чате. Дай краткий анализ: о чём говорят, какое настроение, есть ли конфликты или важные темы."
                },
                {
                    "role": "user",
                    "content": f"Вот последние сообщения из группы:\n\n{conversation}\n\nПроанализируй эту переписку."
                }
            ]
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message()
async def ai_chat(message: types.Message):
    if not message.text:
        return

    is_private = message.chat.type == "private"
    bot_info = await bot.get_me()
    is_mentioned = f"@{bot_info.username}" in message.text

    # В группе — сохраняем все сообщения для анализа
    if not is_private:
        chat_id = message.chat.id
        if chat_id not in group_messages:
            group_messages[chat_id] = []

        # Сохраняем последние 50 сообщений
        sender = message.from_user.first_name or "Аноним"
        group_messages[chat_id].append(f"{sender}: {message.text}")
        if len(group_messages[chat_id]) > 50:
            group_messages[chat_id].pop(0)

        # В группе отвечаем только если упомянули бота
        if not is_mentioned:
            return

       # Убираем упоминание бота из текста
        user_text = message.text.replace(f"@{bot_info.username}", "").strip()

        if not user_text:
            user_text = "Привет! Чем могу помочь?"

    else:
        user_text = message.text

    # Личка — обычный диалог с историей
    user_id = message.from_user.id
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    chat_histories[user_id].append({
        "role": "user",
        "content": user_text
    })

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_histories[user_id]
        )

        answer = response.choices[0].message.content

        chat_histories[user_id].append({
            "role": "assistant",
            "content": answer
        })

        await message.answer(answer)

    except Exception as e:
        print("ERROR:", e)
        await message.answer(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
