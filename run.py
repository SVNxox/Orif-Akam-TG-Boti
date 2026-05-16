import asyncio
from aiohttp import web

from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

from app.bot import bot, dp
from app.config import WEBHOOK_URL

WEBHOOK_PATH = "/webhook"


async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")


def main():
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)

    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()