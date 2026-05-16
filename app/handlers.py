from aiogram import Router
from aiogram.types import Message

from app.regex_utils import extract_numbers
from app.sheets import append_number

router = Router()

async def process_message(message: Message):
    text = message.text or message.caption or ""

    extracted_str = extract_numbers(text)

    if extracted_str:
        await append_number(extracted_number=extracted_str)

@router.message()
async def new_message_handler(message: Message):
    await process_message(message)

@router.edited_message()
async def edited_message_handler(message: Message):
    await process_message(message)