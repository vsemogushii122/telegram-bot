import asyncio
import os
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

db = sqlite3.connect("database.db")
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    premium_until TEXT
)
""")
db.commit()


def register(user_id):
    db.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    db.commit()


def premium_active(user_id):
    row = db.execute(
        "SELECT premium_until FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row or not row[0]:
        return False

    return datetime.fromisoformat(row[0]) > datetime.now()


def give_premium(user_id):
    register(user_id)

    row = db.execute(
        "SELECT premium_until FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    now = datetime.now()

    if row and row[0]:
        old = datetime.fromisoformat(row[0])
        if old > now:
            now = old

    until = now + timedelta(days=30)

    db.execute(
        "UPDATE users SET premium_until=? WHERE user_id=?",
        (until.isoformat(), user_id)
    )
    db.commit()


def menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 Бесплатные материалы", callback_data="free")
    kb.button(text="⭐ Premium", callback_data="premium")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.adjust(1)
    return kb.as_markup()


@dp.message(Command("start"))
async def start(message: Message):
    register(message.from_user.id)

    await message.answer(
        "Добро пожаловать!\n\n"
        "Выбери нужный раздел:",
        reply_markup=menu()
    )


@dp.callback_query(F.data == "free")
async def free(callback: CallbackQuery):
    await callback.message.edit_text(
        "📚 Бесплатные материалы\n\n"
        "Здесь будут размещаться материалы проекта.",
        reply_markup=menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "premium")
async def premium(callback: CallbackQuery):
    if premium_active(callback.from_user.id):
        text = "⭐ У тебя активна Premium-подписка!"
    else:
        text = (
            "⭐ Premium\n\n"
            "Здесь будут доступны дополнительные "
            "материалы проекта."
        )

    await callback.message.edit_text(text, reply_markup=menu())
    await callback.answer()


@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user_id = callback.from_user.id

    if premium_active(user_id):
        row = db.execute(
            "SELECT premium_until FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        date = datetime.fromisoformat(row[0])
        status = f"Premium до {date:%d.%m.%Y}"
    else:
        status = "Бесплатный аккаунт"

    await callback.message.edit_text(
        f"👤 Профиль\n\nID: {user_id}\nСтатус: {status}",
        reply_markup=menu()
    )
    await callback.answer()


@dp.message(Command("give"))
async def give(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    args = message.text.split()

    if len(args) != 2 or not args[1].isdigit():
        await message.answer("Использование: /give USER_ID")
        return

    user_id = int(args[1])
    give_premium(user_id)

    await message.answer("Premium выдан на 30 дней.")

    try:
        await bot.send_message(
            user_id,
            "⭐ Тебе выдан Premium на 30 дней!"
        )
    except Exception:
        pass


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
