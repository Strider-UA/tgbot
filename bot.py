import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq
from telethon import TelegramClient

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
API_ID = int(os.environ.get("api_id"))
API_HASH = os.environ.get("api_hash")
PHONE = os.environ.get("PHONE")
ADMIN_ID = os.environ.get("ADMIN_ID")

client_groq = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
tg_client = TelegramClient("session", API_ID, API_HASH)

chat_histories = {}
group_messages = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    history_key = f"{message.from_user.id}_{message.chat.id}"
    chat_histories[history_key] = []
    await message.answer(
        "Привет! 🤖\n\n"
        "Команды:\n"
        "/analyze — анализ переписки\n"
        "/ask [вопрос] — задай вопрос по переписке\n"
        "/reset — очистить историю"
    )

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
        messages = []
        async with tg_client:
            async for msg in tg_client.iter_messages(message.chat.id, limit=1000):
                if msg.text:
                    sender = getattr(msg.sender, "first_name", "Аноним") or "Аноним"
                    messages.append(f"{sender}: {msg.text}")
        messages.reverse()
        conversation = "\n".join(messages)
        response = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Ты анализируешь переписку в групповом чате. Дай подробный анализ: о чём говорят, какое настроение, есть ли конфликты, важные темы, выводы."
                },
                {
                    "role": "user",
                    "content": f"Вот переписка из группы '{message.chat.title}':\n\n{conversation}\n\nПроанализируй."
                }
            ]
        )
        analysis = response.choices[0].message.content
        await message.answer(f"📊 Анализ:\n\n{analysis}")
        if ADMIN_ID:
            await bot.send_message(
                chat_id=int(ADMIN_ID),
                text=f"📊 Анализ группы *{message.chat.title}*:\n\n{analysis}",
                parse_mode="Markdown"
            )
    except Exception as e:
        print("ERROR:", e)
        await message.answer(f"Ошибка: {e}")

@dp.message(Command("ask"))
async def ask(message: types.Message):
    if message.chat.type == "private":
        await message.answer("Эта команда работает только в группах!")
        return

    # Получаем вопрос после команды /ask
    question = message.text.replace("/ask", "").strip()
    if not question:
        await message.answer("Укажи вопрос! Например:\n/ask найди все суммы с буквой р\n/ask кто кому должен деньги")
        return

    await message.answer("⏳ Читаю историю чата, подожди...")

    try:
        messages = []
        async with tg_client:
            async for msg in tg_client.iter_messages(message.chat.id, limit=1000):
                if msg.text:
                    sender = getattr(msg.sender, "first_name", "Аноним") or "Аноним"
                    messages.append(f"{sender}: {msg.text}")
        messages.reverse()
        conversation = "\n".join(messages)

        response = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник который анализирует переписку в групповом чате и отвечает на вопросы по ней. Отвечай точно и конкретно на вопрос пользователя."
                },
                {
                    "role": "user",
                    "content": f"Вот переписка из группы '{message.chat.title}':\n\n{conversation}\n\nВопрос: {question}"
                }
            ]
        )
        answer = response.choices[0].message.content
        await message.answer(f"💬 Ответ:\n\n{answer}")

        if ADMIN_ID:
            await bot.send_message(
                chat_id=int(ADMIN_ID),
                text=f"❓ Вопрос по группе *{message.chat.title}*:\n{question}\n\n💬 Ответ:\n{answer}",
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

        # Читаем историю чата через Telethon
        await message.answer("⏳ Читаю историю чата, подожди...")
        try:
            messages = []
            async with tg_client:
                async for msg in tg_client.iter_messages(message.chat.id, limit=1000):
                    if msg.text:
                        sender_name = getattr(msg.sender, "first_name", "Аноним") or "Аноним"
                        messages.append(f"{sender_name}: {msg.text}")
            messages.reverse()
            conversation = "\n".join(messages)

            response = client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты помощник который анализирует переписку в групповом чате и отвечает на вопросы по ней. Отвечай точно и конкретно."
                    },
                    {
                        "role": "user",
                        "content": f"Вот переписка из группы '{message.chat.title}':\n\n{conversation}\n\nВопрос: {user_text}"
                    }
                ]
            )
            answer = response.choices[0].message.content
            await message.answer(f"💬 {answer}")
            return
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
            return
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
    await tg_client.start(phone=PHONE)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
