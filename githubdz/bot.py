import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect('logs.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT,
        sender_email TEXT,
        receiver_email TEXT,
        message_text TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

class EmailSending(StatesGroup):
    email = State()
    message_text = State()
    confirm = State()

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Добро пожаловать! Я помогу отправить сообщение на электронную почту.\n"
        "Пожалуйста, введите адрес электронной почты получателя:"
    )
    await state.set_state(EmailSending.email)

@dp.message(EmailSending.email)
async def receive_email(message: types.Message, state: FSMContext):
    email = message.text
    if '@' in email and '.' in email:
        await state.update_data(email=email)
        await message.answer("Отлично! Теперь введите текст сообщения:")
        await state.set_state(EmailSending.message_text)
    else:
        await message.answer("Пожалуйста, введите корректный адрес электронной почты:")

@dp.message(EmailSending.message_text)
async def receive_message_text(message: types.Message, state: FSMContext):
    if message.text.strip():
        await state.update_data(message_text=message.text.strip())
        data = await state.get_data()
        await message.answer(
            f"Вы ввели следующее сообщение:\n\n{data['message_text']}\n\nПолучатель: {data['email']}\n"
            "Отправить сообщение? (Да/Нет)"
        )
        await state.set_state(EmailSending.confirm)
    else:
        await message.answer("Сообщение не может быть пустым. Введите текст сообщения:")

@dp.message(EmailSending.confirm)
async def confirm_or_edit(message: types.Message, state: FSMContext):
    if message.text.lower() == 'да':
        data = await state.get_data()
        email = data['email']
        text = data['message_text']
        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)

            msg = MIMEMultipart()
            msg['From'] = SMTP_EMAIL
            msg['To'] = email
            msg['Subject'] = "Сообщение от Telegram-бота"

            msg.attach(MIMEText(text, 'plain'))

            server.sendmail(SMTP_EMAIL, email, msg.as_string())
            server.quit()

            conn = sqlite3.connect('logs.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO messages (date_time, sender_email, receiver_email, message_text) VALUES (datetime("now"), ?, ?, ?)',
                (SMTP_EMAIL, email, text)
            )
            conn.commit()
            conn.close()

            await message.answer("Сообщение успешно отправлено!")
        except Exception as e:
            await message.answer(f"Произошла ошибка при отправке: {e}")
        await state.clear()
    elif message.text.lower() == 'нет':
        await message.answer("Ок, вы можете заново ввести email или текст сообщения. Введите адрес электронной почты:")
        await state.set_state(EmailSending.email)
    else:
        await message.answer("Пожалуйста, ответьте 'Да' или 'Нет':")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
