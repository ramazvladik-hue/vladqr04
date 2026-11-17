import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 1. Вставьте сюда ваш токен от @BotFather
BOT_TOKEN = os.getenv("8920626227:AAGQlx4D0CPJfCE71ieiCA0cd4MbiRpCbvM")

# Файл для хранения целей и вашего ID
DATA_FILE = "goals_data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Krasnoyarsk") # Укажите ваш часовой пояс

# Клавиатура с удобными кнопками внизу экрана
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Мои цели"), KeyboardButton(text="🧹 Очистить список")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

# Функции для сохранения и загрузки данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"user_id": None, "goals": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Форматирование красивого списка целей
def format_goals(goals):
    if not goals:
        return "На сегодня целей пока нет. Просто напишите мне любую задачу текстом, и я её добавлю!"
    
    lines = ["🎯 <b>Ваши цели на сегодня:</b>\n"]
    for idx, item in enumerate(goals, start=1):
        status = "✅" if item["done"] else "⬜"
        lines.append(f"{idx}. {status} {item['text']}")
    
    lines.append("\n<i>Чтобы отметить цель выполненной, отправьте её номер (например: 1)</i>")
    return "\n".join(lines)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    data = load_data()
    # Запоминаем ваш Telegram ID для рассылки уведомлений
    data["user_id"] = message.from_user.id
    save_data(data)
    
    await message.answer(
        "Привет! Я твой личный трекер целей на день.\n\n"
        "• Чтобы <b>добавить цель</b> — просто напиши её мне в чат.\n"
        "• Чтобы <b>отметить выполненной</b> — отправь её номер из списка.\n"
        "• Я буду напоминать о целях каждый день в <b>09:00</b> и в <b>21:00</b>.",
        reply_markup=main_kb,
        parse_mode="HTML"
    )

# Кнопка "Мои цели" или команда /list
@dp.message(F.text == "📋 Мои цели")
@dp.message(Command("list"))
async def show_goals(message: Message):
    data = load_data()
    await message.answer(format_goals(data["goals"]), parse_mode="HTML")

# Кнопка "Очистить список" или команда /clear
@dp.message(F.text == "🧹 Очистить список")
@dp.message(Command("clear"))
async def clear_goals(message: Message):
    data = load_data()
    data["goals"] = []
    save_data(data)
    await message.answer("Список целей очищен! Можно планировать новые задачи.")

# Кнопка "Помощь"
@dp.message(F.text == "❓ Помощь")
async def show_help(message: Message):
    await message.answer(
        "<b>Как пользоваться ботом:</b>\n"
        "1. Напишите любой текст — бот добавит его как новую цель.\n"
        "2. Отправьте цифру (например, <code>1</code>) — бот отметит цель выполненной (или снимет отметку).\n"
        "3. Нажмите «Мои цели», чтобы проверить прогресс.",
        parse_mode="HTML"
    )

# Обработка любых текстовых сообщений (добавление цели или отметка по номеру)
@dp.message(F.text)
async def handle_text(message: Message):
    data = load_data()
    # Обновляем ID на случай, если /start не нажимали после перезапуска
    if not data["user_id"]:
        data["user_id"] = message.from_user.id

    text = message.text.strip()

    # Если пользователь прислал число — переключаем статус цели
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(data["goals"]):
            data["goals"][idx]["done"] = not data["goals"][idx]["done"]
            save_data(data)
            await message.answer(format_goals(data["goals"]), parse_mode="HTML")
        else:
            await message.answer("Цели с таким номером нет в списке.")
        return

    # Иначе добавляем текст как новую цель
    data["goals"].append({"text": text, "done": False})
    save_data(data)
    await message.answer(f"➕ Цель добавлена!\n\n{format_goals(data['goals'])}", parse_mode="HTML")

# Функция для ежедневных уведомлений по расписанию
async def send_daily_reminder(period: str):
    data = load_data()
    user_id = data.get("user_id")
    if not user_id:
        return

    if period == "morning":
        text = "☀️ <b>Доброе утро!</b> Какие цели поставим на сегодня?\nНапиши их мне в чат.\n\n" + format_goals(data["goals"])
    else:
        text = "🌙 <b>Время подвести итоги дня!</b>\nВот твой список. Отправь номера выполненных задач:\n\n" + format_goals(data["goals"])

    await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")

# Запуск бота и планировщика
async def main():
    # Настройка времени рассылки (часы и минуты)
    scheduler.add_job(send_daily_reminder, "cron", hour=9, minute=0, args=["morning"])
    scheduler.add_job(send_daily_reminder, "cron", hour=21, minute=0, args=["evening"])
    scheduler.start()

    print("Бот успешно запущен! Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
