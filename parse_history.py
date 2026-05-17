import os
import asyncio
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import FloodWait

from app.regex_utils import extract_numbers
from app.sheets import append_message

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHAT_TARGET = int(os.getenv("CHAT_TARGET"))  # -1003826187932
TOPIC_ID = int(os.getenv("TOPIC_ID"))  # 389


async def main():
    app = Client(
        "history_session",
        api_id=API_ID,
        api_hash=API_HASH,
    )

    await app.start()
    print(f"🔌 Telegram sessiyasi boshlandi...")

    # Guruhga kirish huquqini tekshirish
    try:
        chat = await app.get_chat(CHAT_TARGET)
        print(f"✅ Guruh topildi: {chat.title} (ID: {chat.id})")
    except Exception as e:
        print(f"❌ Guruhga kirib bo'lmadi: {e}")
        print("   → Bu akkaunt guruh a'zosi ekanligiga ishonch hosil qiling.")
        await app.stop()
        return

    print(f"📥 Topic {TOPIC_ID} tarixini yuklash boshlandi...")
    processed = 0
    saved = 0
    skipped = 0

    # Barcha xabarlarni ketma-ket o'qish
    async for message in app.get_chat_history(CHAT_TARGET):
        processed += 1

        # ✅ Topic ID filtri (Eng muhim qism)
        msg_thread_id = getattr(message, 'message_thread_id', None)

        # Agar xabar topicga tegishli bo'lmasa, o'tkazib yuborish
        if msg_thread_id != TOPIC_ID:
            skipped += 1
            continue

        # Debug: birinchi topilgan xabarni tekshirish
        if processed == 1 and msg_thread_id == TOPIC_ID:
            print(f"🔍 Birinchi xabar topildi: ID={message.id}, ThreadID={msg_thread_id}")

        text = message.text or message.caption or ""
        if not text.strip():
            continue  # Bo'sh yoki faqat rasmli xabarlarni o'tkazish

        number = extract_numbers(text)
        if not number:
            continue

        try:
            await append_message(
                extracted_number=number,
                message_text=text,
                message_date=str(message.date.astimezone(ZoneInfo("Asia/Tashkent"))),
                tg_link=message.link or "",
            )
            saved += 1
            print(f"✅ Saqlandi: #{message.id} | Raqam: {number}")

        except FloodWait as e:
            print(f"⏳ FloodWait: {e.value} soniya kutish...")
            await asyncio.sleep(e.value)
            await append_message(
                extracted_number=number,
                message_text=text,
                message_date=str(message.date.astimezone(ZoneInfo("Asia/Tashkent"))),
                tg_link=message.link or "",
            )
            saved += 1

        except Exception as e:
            print(f"❌ Xatolik #{message.id}: {e}")
            continue

    await app.stop()
    print(f"\n🎉 TUGADI!")
    print(f"   Jami ko'rilgan xabarlar: {processed}")
    print(f"   Boshqa topiclardan o'tkazib yuborilgan: {skipped}")
    print(f"   Saqlangan (389-topic): {saved}")


if __name__ == "__main__":
    asyncio.run(main())