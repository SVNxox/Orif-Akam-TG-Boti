from aiogram import Router, F
from aiogram.types import Message
from zoneinfo import ZoneInfo
from app.regex_utils import extract_numbers
from app.sheets import append_message

from app.config import TOPIC_ID, CHAT_TARGET

router = Router()


async def process_message(message: Message):
    # 🔹 Фильтр 1: только сообщения из нужного чата
    if message.chat.id != CHAT_TARGET:
        return

    # 🔹 Фильтр 2: только сообщения из нужного топика
    # Если message_thread_id нет — это обычное сообщение (не из топика)
    if getattr(message, "message_thread_id", None) != TOPIC_ID:
        return

    # 🔹 Опционально: игнорировать сообщения от ботов (включая себя)
    if message.from_user and message.from_user.is_bot:
        return

    text = message.text or message.caption or ""
    extracted_num = extract_numbers(text)

    if extracted_num:
        extracted_num = int(extracted_num)

    if text:
        await append_message(
            extracted_number=extracted_num,
            message_text=text,
            message_date=str(message.date.astimezone(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")),
            tg_link=str(message.get_url())
        )


# 🔹 Добавляем фильтр на уровне роутера (о   пционально, для экономии ресурсов)
@router.message(F.chat.id == CHAT_TARGET)
async def new_message_handler(message: Message):
    await process_message(message)


@router.edited_message(F.chat.id == CHAT_TARGET)
async def edited_message_handler(message: Message):
    await process_message(message)