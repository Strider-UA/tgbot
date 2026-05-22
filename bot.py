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

chat_histories = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    chat_histories[message.from_user.id] = []
    await message.answer("Привет! Задай мне любой вопрос 🤖")

@dp.message(Command("reset"))
async def reset(message: types.Message):
    chat_histories[message.from_user.id] = []
    await message.answer("История очищена! Начнём заново 🔄")

@dp.message()
async def ai_chat(message: types.Message):
    user_id = message.from_user.id

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    # Добавляем сообщение пользователя в историю
    chat_histories[user_id].append({
        "role": "user",
        "content": message.text
    })

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_histories[user_id]
        )

        answer = response.choices[0].message.content

        # Сохраняем ответ в историю
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