from aiogram import Router
from aiogram.types import Message
from zoneinfo import ZoneInfo
from app.regex_utils import extract_numbers
from app.sheets import append_message

router = Router()

async def process_message(message: Message):
    text = message.text or message.caption or ""

    extracted_num = extract_numbers(text)

    if extracted_num:
        extracted_num = int(extracted_num)

    if text!="":
        await append_message(extracted_number=extracted_num, message_text=text, message_date=str(message.date.astimezone(ZoneInfo("Asia/Tashkent"))), tg_link=str(message.get_url()))

@router.message()
async def new_message_handler(message: Message):
    await process_message(message)

@router.edited_message()
async def edited_message_handler(message: Message):
    await process_message(message)