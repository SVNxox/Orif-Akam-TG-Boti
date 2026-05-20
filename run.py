import asyncio
import os
import ssl
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Update
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from app.bot import bot, dp
from app.config import WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH, WEBHOOK_SECRET, ADMIN_IDS, CHAT_TARGET, SHEET_NAME
from app.sheets import client_manager, delete_row_by_message_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8443


# ─────────────────────────────────────────────
# 🗑️ Обработка удалённых сообщений пользователей
# ─────────────────────────────────────────────

async def handle_deleted_messages(raw_update: dict):
    """
    Telegram Bot API >= 7.0 отправляет updates с полем 'deleted_messages'
    когда пользователь (или admin) удаляет сообщение из группы.

    Формат:
    {
        "update_id": ...,
        "deleted_messages": {
            "chat": {"id": ..., ...},
            "message_ids": [111, 222, ...],
            "from_user": {...} # кто удалил (опционально)
        }
    }sync

    Примечание: Telegram Bot API пока НЕ поддерживает стандартный update
    для удалённых пользователем сообщений в группах — это ограничение платформы.
    Единственный надёжный способ — auto_sync_loop + /sync.
    Этот хэндлер обрабатывает случаи, если в будущем Telegram добавит такой update.
    """
    deleted = raw_update.get("deleted_messages")
    if not deleted:
        return

    chat = deleted.get("chat", {})
    chat_id = chat.get("id")
    message_ids = deleted.get("message_ids", [])

    if not chat_id or not message_ids:
        return

    for msg_id in message_ids:
        try:
            result = await delete_row_by_message_id(
                message_id=msg_id,
                chat_id=chat_id
            )
            if result:
                logger.info(f"🗑️ Deleted row for message {msg_id} (deleted_messages update)")
            else:
                logger.debug(f"ℹ️ No row found for deleted message {msg_id}")
        except Exception as e:
            logger.error(f"❌ Error handling deleted message {msg_id}: {e}")


# ─────────────────────────────────────────────
# 🔄 Авто-синхронизация (фоновая задача)
# ─────────────────────────────────────────────

async def auto_sync_loop():
    """
    Фоновая задача: только логирует статус.
    ⚠️ Telegram Bot API НЕ позволяет проверять сообщения по ID.
    """
    if not ADMIN_IDS or not SHEET_NAME:
        logger.warning("⚠️ ADMIN_ID или SHEET_NAME не задан")
        return

    logger.info("⏳ Авто-синхронизация запущена (только логирование)")
    await asyncio.sleep(60)

    while True:
        try:
            logger.info("🔄 Авто-синхронизация: проверка (логирование)...")
            # Просто логируем — реальная проверка невозможна через Bot API
            logger.info("✅ Авто-синхронизация: для уsyncдаления используйте /sync вручную")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}", exc_info=True)
        await asyncio.sleep(14400)  # 4 часа


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────

async def on_startup(app):
    await bot.set_webhook(
        f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        # Разрешаем получать все типы обновлений включая удаления (если Telegram добавит)
        allowed_updates=[
            "message",
            "edited_message",
            "callback_query",
            "inline_query",
            "chosen_inline_result",
            "channel_post",
            "edited_channel_post",
            "deleted_messages",       # на будущее
        ]
    )
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}{WEBHOOK_PATH}")

    asyncio.create_task(auto_sync_loop())
    logger.info("🔄 Фоновая задача синхронизации запущена (интервал: 4 часа)")


# ─────────────────────────────────────────────
# Кастомный webhook-хэндлер с поддержкой deleted_messages
# ─────────────────────────────────────────────

class ExtendedRequestHandler(SimpleRequestHandler):
    """
    Расширяет стандартный SimpleRequestHandler aiogram:
    перед передачей update в диспетчер проверяет наличие
    поля 'deleted_messages' и обрабатывает его отдельно.
    """
    async def handle(self, request: web.Request) -> web.Response:
        # Читаем raw JSON
        try:
            raw_data = await request.json()
        except Exception:
            return web.Response(status=400)

        # Обрабатываем удалённые сообщения (если Telegram прислал такое поле)
        if "deleted_messages" in raw_data:
            asyncio.create_task(handle_deleted_messages(raw_data))

        # Отдаём стандартному хэндлеру aiogram
        return await super().handle(request)


def main():
    app = web.Application()

    ExtendedRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)

    logger.info(f"🚀 Запуск сервера на {WEB_SERVER_HOST}:{WEB_SERVER_PORT} (HTTPS)")

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, ssl_context=ssl_context)


if __name__ == "__main__":
    main()