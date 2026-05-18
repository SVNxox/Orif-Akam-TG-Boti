import asyncio
import os
import ssl

from aiohttp import web

from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

from app.bot import bot, dp
from app.config import WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH, WEBHOOK_SECRET

WEBHOOK_PATH = "/webhook"
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8443


async def on_startup(app):
    await bot.set_webhook(
        f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET
    )
    print(f"✅ Webhook установлен: {WEBHOOK_URL}{WEBHOOK_PATH}")


def main():
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)

    print(f"🚀 Запуск сервера на {WEB_SERVER_HOST}:{WEB_SERVER_PORT} (HTTPS)")
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, ssl_context=ssl_context)


if __name__ == "__main__":
    main()