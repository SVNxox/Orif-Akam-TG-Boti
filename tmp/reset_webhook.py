import os, sys, asyncio
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/orif_akam_tg_bot/.env')
from aiogram import Bot

async def main():
    bot = Bot(os.getenv('BOT_TOKEN'))
    # Удаляем старый вебхук
    await bot.delete_webhook()
    # Устанавливаем новый
    await bot.set_webhook(f"{os.getenv('WEBHOOK_URL')}/webhook")
    info = await bot.get_webhook_info()
    print(f"✅ Webhook: {info.url}")
    print(f"✅ Pending: {info.pending_update_count}")
    await bot.session.close()

asyncio.run(main())