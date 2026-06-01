from aiogram import Router, F
from aiogram.types import Message
from zoneinfo import ZoneInfo
import logging

from app.regex_utils import extract_numbers
from app.sheets import (
    append_message,
    update_row_by_message_id,
    delete_row_by_message_id,
    client_manager,
    find_row_by_message_id
)
from app.access import add_user, remove_user, is_allowed_user
from app.config import CHAT_TARGET, TOPIC_ID, ADMIN_IDS, SHEET_NAME
import asyncio

logger = logging.getLogger(__name__)
router = Router()


async def process_group_message(message: Message, is_edit: bool = False):
    """
    Обрабатывает сообщения из группы и отправляет/обновляет в Google Sheets.
    is_edit=True → обновляем существующую строку
    is_edit=False → создаём новую строку
    """
    if message.chat.id != CHAT_TARGET:
        return

    msg_thread_id = getattr(message, "message_thread_id", None)
    if TOPIC_ID and msg_thread_id != TOPIC_ID:
        return

    if message.from_user and message.from_user.is_bot:
        return

    text = message.text or message.caption or ""
    if not text.strip():
        return

    extracted_num = extract_numbers(text)
    extracted_number = int(extracted_num) if extracted_num else None

    tg_link = ""
    if message.sender_chat:
        title = (message.sender_chat.title or "Anonim chat").replace('"', '""')
        if message.sender_chat.username:
            tg_link = f'=HYPERLINK("https://t.me/{message.sender_chat.username}"; "{title}")'
        else:
            tg_link = f"{title} (Yashirin chat)"
    elif message.from_user and message.from_user.username:
        full_name = (message.from_user.full_name or "Ismi yo'q").replace('"', '""')
        tg_link = f'=HYPERLINK("https://t.me/{message.from_user.username}"; "{full_name}")'
    elif message.from_user:
        tg_link = f'=HYPERLINK("tg://user?id={message.from_user.id}"; "ID: {message.from_user.id}")'

    post_url = ""
    if CHAT_TARGET < 0:
        chat_id_clean = str(CHAT_TARGET).replace("-100", "")
        if TOPIC_ID:
            post_url = f"https://t.me/c/{chat_id_clean}/topic/{TOPIC_ID}/{message.message_id}"
        else:
            post_url = f"https://t.me/c/{chat_id_clean}/{message.message_id}"
    elif message.chat.username:
        post_url = f"https://t.me/{message.chat.username}/{message.message_id}"

    sent_timestamp = message.date.astimezone(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")

    if is_edit:
        new_id = int(extracted_num) if extracted_num else None
        updated = await update_row_by_message_id(
            message_id=message.message_id,
            chat_id=CHAT_TARGET,
            message_text=text,
            extracted_number=extracted_num
        )
        if updated:
            logger.info(f"✅ Updated row for message {message.message_id} (ID: {new_id})")
        else:
            await append_message(
                extracted_number=extracted_number,
                message_text=text,
                tg_link=tg_link,
                post_url=post_url,
                sent_timestamp=sent_timestamp,
                message_id=message.message_id,
                chat_id=CHAT_TARGET
            )
            logger.info(f"✅ Created new row for edited message {message.message_id}")
        return

    try:
        await append_message(
            extracted_number=extracted_number,
            message_text=text,
            tg_link=tg_link,
            post_url=post_url,
            sent_timestamp=sent_timestamp,
            message_id=message.message_id,
            chat_id=CHAT_TARGET
        )
        logger.info(f"✅ Added new row for message {message.message_id}")
    except Exception as e:
        logger.error(f"❌ Sheets error for message {message.message_id}: {e}")


# ─────────────────────────────────────────────
# Хэндлеры: новые и отредактированные сообщения
# ─────────────────────────────────────────────

@router.message(F.chat.id == CHAT_TARGET)
async def group_message_handler(message: Message):
    await process_group_message(message, is_edit=False)


@router.edited_message(F.chat.id == CHAT_TARGET)
async def group_edited_message_handler(message: Message):
    await process_group_message(message, is_edit=True)


# ─────────────────────────────────────────────
# /sync — ручная синхронизация (только ADMIN_ID)
# ─────────────────────────────────────────────

@router.message(F.text == "/yangilash")
async def sync_deleted_posts(message: Message):
    """
    ⚠️ Telegram Bot API не позволяет проверять удаление чужих сообщений.
    Эта команда только показывает статистику.
    """
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🔒 Faqat admin uchun")
        return

    try:
        client = await client_manager.authorize()
        spreadsheet = await client.open(SHEET_NAME)
        sheet = await spreadsheet.get_worksheet(0)
        all_values = await sheet.get_values()

        if len(all_values) < 2:
            await message.answer("✅ Jadval bo'sh")
            return

        headers = all_values[0]
        msg_id_col = headers.index("Message_ID") if "Message_ID" in headers else -1

        if msg_id_col == -1:
            await message.answer("❌ Message_ID ustuni topilmadi")
            return

        # Считаем валидные записи
        count = sum(1 for row in all_values[1:] if len(row) > msg_id_col and str(row[msg_id_col]).strip().isdigit())

        await message.answer(
            f"✅ Statistika:\n"
            f"📊 Jadvaldagi yozuvlar soni: <b>{count}</b>\n\n"
            f"⚠️ Telegram Bot API xabarlar o‘chirilishini avtomatik kuzatish imkonini bermaydi.\n"
            f"Satrlarni qo‘lda o‘chirish uchun jadvalni oching va kerak bo‘lmagan yozuvlarni o‘chirib tashlang.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Sync error: {e}", exc_info=True)
        await message.answer(f"❌ Xato: {e}")


# 🔹 /ruxsat <ID> [Имя] — добавить пользователя с опциональным именем
@router.message(F.text.startswith("/ruxsat"))
async def cmd_allow(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("🔒 Faqat admin uchun.")

    # Разделяем строку команды по пробелам, максимум на 3 части:
    # ['/ruxsat', '12345678', 'Abror MFY']
    parts = message.text.split(maxsplit=2)

    if len(parts) < 2:
        return await message.answer("❌ Format: `/ruxsat 123456789 Abror MFY` (ism ixtiyoriy)", parse_mode="Markdown")

    uid_str = parts[1]
    name_str = parts[2] if len(parts) > 2 else ""

    if not uid_str.isdigit():
        return await message.answer("❌ ID faqat raqamlardan iborat bo'lishi kerak.")

    uid = int(uid_str)

    # add_user теперь принимает и имя. Если запись обновилась/создалась, вернет True
    if add_user(uid, name_str):
        if name_str:
            await message.answer(f"✅ ID <code>{uid}</code> (<i>{name_str}</i>) oq roʻyxatga qoʻshildi/yangilandi.",
                                 parse_mode="HTML")
        else:
            await message.answer(f"✅ ID <code>{uid}</code> oq roʻyxatga qoʻshildi.", parse_mode="HTML")
    else:
        await message.answer(
            f"ℹ️ ID <code>{uid}</code> uchun ma'lumotlar o'zgarmadi (allaqachon xuddi shunday ro'yhatda bor).",
            parse_mode="HTML")


# 🔹 /haydash <ID> — убрать пользователя
@router.message(F.text.startswith("/haydash"))
async def cmd_remove(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("🔒 Faqat admin uchun.")

    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("❌ Format: `/haydash 123456789`", parse_mode="Markdown")

    uid_str = parts[1]
    if not uid_str.isdigit():
        return await message.answer("❌ ID faqat raqamlardan iborat bo'lishi kerak.")

    uid = int(uid_str)
    if remove_user(uid):
        await message.answer(f"🚫 ID <code>{uid}</code> oq ro'yhatdan o'chirildi.", parse_mode="HTML")
    else:
        await message.answer(f"ℹ️ ID <code>{uid}</code> ro'yhatda topilmadi.", parse_mode="HTML")


# 🔹 /azolar — показать текущий список с юзернеймами и именами
@router.message(F.text == "/azolar")
async def cmd_list_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("🔒 Faqat admin uchun.")

    from app.access import get_all_users
    users = get_all_users()  # Получаем словарь {uid: name}

    if not users:
        return await message.answer("📋 Oq ro'yhat bo'sh.")

    response_lines = []

    for uid, name in users.items():
        username_part = ""
        try:
            # Запрашиваем информацию у Telegram API для получения юзернейма
            chat = await message.bot.get_chat(uid)
            if chat.username:
                username_part = f"(@{chat.username})"
        except Exception:
            # Ошибка будет, если бот никогда не «видел» этого пользователя
            pass

        # Форматируем строку вывода
        if name:
            line = f"• <code>{uid}</code>{username_part} - {name}"
        else:
            line = f"• <code>{uid}</code>{username_part}"

        response_lines.append(line)

    text = f"📋 Ruxsat berilgan foydalanuvchilar ({len(users)}):\n" + "\n".join(response_lines)
    await message.answer(text, parse_mode="HTML")