from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers import router

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN kiritilmagan")

bot = Bot(BOT_TOKEN)

dp = Dispatcher()

dp.include_router(router)