from aiogram import Router, F
from aiogram.types import Message
from pyrogram.raw.functions.messages import get_scheduled_messages

from app.handlers.form import load_mapping, get_mapping_key, save_mapping
from app.sheets import delete_row_by_message_id, update_row_by_id, find_row_by_message_id, update_message_ids

sync_router =Router()


@sync_router.message_delete()
async def on_message_delete(message: Message):
    chat_id = message.chat.id
    message_id = message.message_id

    deleted = await delete_row_by_message_id(message_id, chat_id)

    if deleted:
        mapping = load_mapping()
        key = get_mapping_key(chat_id, message_id)
        if key in mapping:
            del mapping[key]
            save_mapping(mapping)


# Xabar o'zgarganda ishlaydi
@sync_router.message(F.edit_date)
async def on_message_edited(message: Message):
    chat_id = message.chat.id
    message_id = message.message_id

    row_num = await find_row_by_message_id(message_id, chat_id)
    if not row_num:
        return

    # Ma'lumotlar yangilanish logikasi
    if message.caption:
        await update_row_by_id(
            row_number=row_num,
            message_text=message.caption
        )