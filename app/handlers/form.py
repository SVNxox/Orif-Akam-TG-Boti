from app.access import is_allowed_user
from app.keyboards import (
    get_main_keyboard,
    get_back_keyboard,
    get_submit_keyboard,
    get_edit_fields_keyboard,
    get_mfy_inline_keyboard,
)
import json
import os
import re
import asyncio
from datetime import datetime, timezone

from aiogram import Router, F, html
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup, InputMediaDocument,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.exceptions import TelegramBadRequest
from zoneinfo import ZoneInfo

from app.sheets import append_message, update_message_ids
from app.config import CHAT_TARGET, TOPIC_ID, ADMIN_IDS
from app.regex_utils import extract_numbers

import logging
logger = logging.getLogger(__name__)

form_router = Router()

# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
@form_router.message(F.text == "/start")
async def global_start(message: Message, state: FSMContext):
    """Перезапуск бота из любого состояния"""
    if not is_allowed_user(message.from_user.id):
        await message.answer(
            "🔒 <b>Kirish cheklangan</b>\n\n"
            "Sizda ushbu formadan foydalanish huquqi yo'q.\n"
            "Agar bu xato bo'lsa, admin bilan bog'laning.",
            parse_mode="HTML"
        )
        return
    await state.clear()
    await cmd_start(message)
    

@form_router.message(F.text == "/start")
async def cmd_start(message: Message):
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {html.quote(message.from_user.first_name)}!</b>\n\n"
        "🤖 Ushbu bot fotosuratlarga ega arizalarni yuborishda yordam beradi.\n\n"
        "📋 <b>Foydalanish tartibi:</b>\n"
        "1️⃣ «📝 Formani to'ldirish» tugmasini bosing\n"
        "2️⃣ ID, Familiya Ism Sharifni ni kiriting \nMFY va sanani tanlang\n"
        "3️⃣ 1 tadan 10 tagacha rasm yuboring\n"
        "4️⃣ Oldindan ko'rishni tekshiring va «✅ Yuborish» tugmasini bosing\n\n"
        "❓ Yordam kerakmi? «❓ Yo'riqnoma» tugmasini bosing."
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


# Bosqichalar
class FormState(StatesGroup):
    waiting_for_id = State()
    waiting_for_fish = State()
    waiting_for_mfy = State()
    waiting_for_sana = State()
    waiting_for_photos = State()

# Albom IDsi, span qilmasligi uchun
ALBUM_LOCKS = set()

MAPPING_FILE = "message_mapping.json"

# Yuborish va tahrirlash tugmalari
def get_submit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="form:submit"),
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="form:edit_menu"),
    )
    return builder.as_markup()


# Maydonlarni tanlash menyusi
def get_edit_fields_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🔢 ID", callback_data="edit:id"),
        InlineKeyboardButton(text="👤 F.I.Sh.", callback_data="edit:fish"),
    )
    builder.row(
        InlineKeyboardButton(text="🏢 MFY", callback_data="edit:mfy"),
        InlineKeyboardButton(text="📅 Sana", callback_data="edit:sana"),
    )
    builder.row(InlineKeyboardButton(text="📸 Rasmlar", callback_data="edit:photos"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="edit:cancel"))
    return builder.as_markup()


# Preview matni
def build_preview_text(data: dict) -> str:
    return (
        f"ID: {data.get('id')}\n"
        f"{html.quote(data.get('fish'))}\n"
        f"{data.get('mfy')}\n"
        f"{data.get('sana')}"
    )


def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def get_mapping_key(chat_id: int, message_id: int) -> str:
    return f"{chat_id}:{message_id}"


# Forma boshlash handleri
@form_router.message(F.text.in_(["📝 Formani to'ldirish", "/form"]))
async def start_form(message: Message, state: FSMContext):
    if not is_allowed_user(message.from_user.id):
        await message.answer(
            "🔒 <b>Kirish cheklangan</b>\n\n"
            "Sizda ushbu formadan foydalanish huquqi yo'q.\n"
            "Agar bu xato bo'lsa, admin bilan bog'laning.",
            parse_mode="HTML"
        )
        return

    await state.clear()
    await state.set_state(FormState.waiting_for_id)

    await message.answer(
        "🔢 <b>1/5-qadam: ID raqamini kiriting</b>\n\n",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


# ID handleri
@form_router.message(FormState.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    if message.text == "🔙 Menyuga qaytish":
        await state.clear()
        await message.answer(
            "✅ Forma bekor qilindi. Harakatni tanlang:",
            reply_markup=get_main_keyboard()
        )
        return
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer(
            "✅ Forma bekor qilindi. Harakatni tanlang:",
            reply_markup=get_main_keyboard()
        )
        return

    extracted = extract_numbers(message.text)
    if not extracted:
        await message.answer("❌ ID raqami faqat raqamlardan iborat bo'lishi kerak. \nQaytadan urinib ko'ring.:")
        return

    await state.update_data(id=extracted)
    data = await state.get_data()

    if data.get("is_editing"):
        await state.update_data(is_editing=False)
        await state.set_state(FormState.waiting_for_photos)
        text = build_preview_text({**data, "id": extracted})
        msg = await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_submit_keyboard()
        )
        await state.update_data(last_msg_id=msg.message_id)
        return

    # FISH handleriga o'tadi
    await state.set_state(FormState.waiting_for_fish)
    await message.answer(
        f"✅ ID: <code>{extracted}</code>\n\n"
        "👤 <b>2/5-qadam: Familiya Ism Sharifni kiriting</b>",
        parse_mode="HTML"
    )


# F.I.Sh. handleri
@form_router.message(FormState.waiting_for_fish)
async def process_fish(message: Message, state: FSMContext):
    if message.text == "🔙 Menyuga qaytish":
        await state.clear()
        await message.answer("✅ Forma bekor qilindi.", reply_markup=get_main_keyboard())
        return
    if message.text == "🔙 Orqaga":  # Возврат на шаг назад
        await state.set_state(FormState.waiting_for_id)
        await message.answer("🔢 Yangi ID kiriting:", reply_markup=get_back_keyboard())
        return

    fish = message.text.strip()

    await state.update_data(fish=fish)
    data = await state.get_data()

    if data.get("is_editing"):
        await state.update_data(is_editing=False)
        await state.set_state(FormState.waiting_for_photos)
        text = build_preview_text({**data, "fish": fish})
        msg = await message.answer(text, parse_mode="HTML", reply_markup=get_submit_keyboard())
        await state.update_data(last_msg_id=msg.message_id)
        return

    #MFY handleriga o'tiga
    await state.set_state(FormState.waiting_for_mfy)
    await message.answer(
        f"✅ <b>{html.quote(fish)}</b>\n\n"
        "🏢 <b>3/5-qadam: MFY ni tanlang</b>",
        parse_mode="HTML",
        reply_markup=get_mfy_inline_keyboard()
    )


MFY_OPTIONS = {
        "Адиробод МФЙ": "01", "Андижон МФЙ": "02", "Дўстлик МФЙ": "03",
        "Ёшлик МФЙ": "04", "Лалмикор МФЙ": "05", "Мустақиллик МФЙ": "06",
        "Навбаҳор МФЙ": "07", "Навоий МФЙ": "08", "Наврўз МФЙ": "09",
        "Нурафшон МФЙ": "10", "Нуробод МФЙ": "11", "Ойбек МФЙ": "12",
        "Оқар МФЙ": "13", "Оқбулоқ МФЙ": "14", "Равот МФЙ": "15",
        "Тараққиёт МФЙ": "16", "Тинчлик МФЙ": "17", "Тошкесган МФЙ": "18",
        "Шарқ Юлдузи МФЙ": "19", "Шодлик МФЙ": "20", "Янгиҳаёт МФЙ": "21",
        "Янгикент МФЙ": "22", "Янгиобод МФЙ": "23"
    }


# 📍 MFY bosqichida navigatsiya
@form_router.message(FormState.waiting_for_mfy, F.text == "🔙 Orqaga")
async def mfy_step_back(message: Message, state: FSMContext):
    """MFY → F.I.Sh. ga qaytish"""
    await state.set_state(FormState.waiting_for_fish)
    await message.answer(
        "👤 <b>2/5 Qadam: F.I.Sh. ni kiriting</b>\n\n"
        "Familiya, Ism, Sharifni to'liq yozing:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@form_router.message(FormState.waiting_for_mfy, F.text.in_(["🔙 Menyuga qaytish", "🔙 Bekor qilish", "/cancel"]))
async def mfy_cancel(message: Message, state: FSMContext):
    """Formani butunlay bekor qilish"""
    await state.clear()
    await message.answer(
        "✅ Forma bekor qilindi. Bosh menyuga qaytdingiz.",
        reply_markup=get_main_keyboard()
    )

# 📍 Photos bosqichida navigatsiya
@form_router.message(FormState.waiting_for_photos, F.text == "🔙 Orqaga")
async def photos_step_back(message: Message, state: FSMContext):
    """Photos → Sana ga qaytish"""
    await state.set_state(FormState.waiting_for_sana)
    await message.answer(
        "📅 <b>4/5 Qadam: Sana kiriting</b>\n\n"
        "Format: 07.05.2026:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@form_router.message(FormState.waiting_for_photos, F.text.in_(["🔙 Menyuga qaytish", "🔙 Bekor qilish", "/cancel"]))
async def photos_cancel(message: Message, state: FSMContext):
    """Formani butunlay bekor qilish"""
    await state.clear()
    await message.answer(
        "✅ Forma bekor qilindi. Bosh menyuga qaytdingiz.",
        reply_markup=get_main_keyboard()
    )

#MFY handleri
@form_router.callback_query(FormState.waiting_for_mfy, F.data.startswith("mfy:"))
async def process_mfy(callback: CallbackQuery, state: FSMContext):
    #MFY tanlashini kutish
    await callback.answer()

    #Orqaga FISHga qaytish
    if callback.data == "mfy:back":
        await state.set_state(FormState.waiting_for_fish)
        await callback.message.edit_text(
            "2️⃣ <b>F.I.Sh.</b> (Ism Familiya Sharif) ni kiriting:",
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )
        return

    mfy_value = callback.data.split(":")[1]
    mfy_name = [k for k, v in MFY_OPTIONS.items() if mfy_value == v][0]

    # MFYni vaqtincha xotiraga saqlab turadi
    await state.update_data(mfy=mfy_name, mfy_code=mfy_value)
    data = await state.get_data()

    # Agar editing rejimida bo'lsa -> Previewga qaytish
    if data.get("is_editing"):
        await state.update_data(is_editing=False)
        await state.set_state(FormState.waiting_for_photos)
        text = build_preview_text({**data, "mfy": mfy_name})
        msg = await callback.message.answer(text, parse_mode="HTML", reply_markup=get_submit_keyboard())
        await state.update_data(last_msg_id=msg.message_id)
        return

    # Sana handleriga o'tadi
    await state.set_state(FormState.waiting_for_sana)
    await callback.message.edit_text(
        f"✅ <b>{mfy_name}</b>\n\n"
        "📅 <b>Qadam 4/5: Sanani kiriting</b>\n\n"
        "Format: 07.05.2026:",
        parse_mode="HTML",
        reply_markup=None
    )

# Sana handleri
@form_router.message(FormState.waiting_for_sana)
async def process_sana(message: Message, state: FSMContext):
    if message.text == "🔙 Menyuga qaytish":
        await state.clear()
        await message.answer("✅ Forma bekor qilindi.", reply_markup=get_main_keyboard())
        return
    if message.text == "🔙 Orqaga":
        await state.set_state(FormState.waiting_for_mfy)
        await message.answer("🏢 MFY tanlang:", reply_markup=get_mfy_inline_keyboard())
        return

    sana = message.text.strip()

    # Validatsiya: 1 va undan ko'p probel/to'chka/defis ishlatsa bo'ladi
    if not re.match(r"\d{1,2}[\s./-]+\d{1,2}[\s./-]+\d{2,4}$", sana):
        await message.answer(
            "❌ Sanani to'g'ri formatda kiriting (masalan 07.05.20026:):"
        )
        return

    # Sanani 07.07.2026 formatga o'zgartiradi
    clean_sana = re.sub(r"[\s./-]+", ".", sana)

    # Sanani vaqtincha xotiraga saqlab turadi
    await state.update_data(sana=clean_sana)
    data = await state.get_data()

    # Agar editing rejimida bo'lsa -> Previewga qaytish
    if data.get("is_editing"):
        await state.update_data(is_editing=False)
        await state.set_state(FormState.waiting_for_photos)
        text = build_preview_text({**data, "sana": clean_sana})
        msg = await message.answer(text, parse_mode="HTML", reply_markup=get_submit_keyboard())
        await state.update_data(last_msg_id=msg.message_id)
        return

    # Photos handleriga o'tadi
    await state.set_state(FormState.waiting_for_photos)
    await message.answer(
        f"✅ Sana: <b>{clean_sana}</b>\n\n"
        "📸 <b>Qadam 5/5: Rasm yuboring</b>\n\n"
        "• 1-10 rasm yuborsa bo'ladi\n"
        "📤 Tayyor bo'lgach jo'natish tugmasini bosing",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


# Photo handleri
@form_router.message(
    FormState.waiting_for_photos,
    (F.photo | (F.document & F.document.mime_type.startswith("image/")))
)
async def process_photos(message: Message, state: FSMContext):
    if message.text == "🔙 Menyuga qaytish":
        await state.clear()
        await message.answer("✅ Forma bekor qilindi.", reply_markup=get_main_keyboard())
        return
    if message.text == "🔙 Orqaga":
        await state.set_state(FormState.waiting_for_sana)
        await message.answer("📅 Yangi sanani kiriting:", reply_markup=get_back_keyboard())
        return

    data = await state.get_data()
    photos = data.get("photos", [])

        # 🔍 Fayl turini va file_id ni aniqlash
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.document and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id
        media_type = "document"
    else:
        await message.answer("❌ Iltimos, faqat rasm fayllarini (JPG, PNG, WEBP) yuboring.")
        return

    # Limitdan oshmaganini tekshirish
    if len(photos) >= 10:
        if message.media_group_id not in ALBUM_LOCKS:
            ALBUM_LOCKS.add(message.media_group_id)
            await message.answer("⚠️ Maksimum 10 ta rasim qabul qilinadi")
        return

        # Rasmni tur bilan birga saqlash
    photos.append({"type": media_type, "id": file_id})
    await state.update_data(photos=photos)

    # Preview matni
    def build_preview(d):
        return (
            f"ID: {d.get('id')}\n"
            f"{html.quote(d.get('fish'))}\n"
            f"{d.get('mfy')}\n"
            f"{d.get('sana')}\n"
        )

    # Oldingi previewni o'chirish
    last_msg_id = data.get("last_msg_id")
    if last_msg_id:
        try:
            await message.bot.delete_message(message.chat.id, last_msg_id)
        except:
            pass

    if message.media_group_id:
        if message.media_group_id not in ALBUM_LOCKS:
            ALBUM_LOCKS.add(message.media_group_id)
            await asyncio.sleep(0.5)
            current_data = await state.get_data()
            msg = await message.answer(
                build_preview(current_data),
                parse_mode="HTML",
                reply_markup=get_submit_keyboard()
            )
            await state.update_data(last_msg_id=msg.message_id)
            ALBUM_LOCKS.discard(message.media_group_id)
    else:
        msg = await message.answer(
            build_preview(data),
            parse_mode="HTML",
            reply_markup=get_submit_keyboard()
        )
        await state.update_data(last_msg_id=msg.message_id)


# Tahrirlash menyusi
@form_router.callback_query(FormState.waiting_for_photos, F.data == "form:edit_menu")
async def show_edit_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "✏️ <b>Qaysi ma'lumotni o'zgartirmmoqchisiz?</b>\n\n"
        "Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=get_edit_fields_keyboard()
    )


# Maydonlarni tanlash va tahrirlash
@form_router.callback_query(FormState.waiting_for_photos, F.data.startswith("edit:"))
async def process_field_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":")[1]

    if choice == "cancel":
        data = await state.get_data()
        text = build_preview_text(data)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_submit_keyboard())
        return

    await state.update_data(is_editing=True)

    if choice == "id":
        await state.set_state(FormState.waiting_for_id)
        await callback.message.answer("🔢 Yangi <b>ID</b> kiriting:", parse_mode="HTML")
    elif choice == "fish":
        await state.set_state(FormState.waiting_for_fish)
        await callback.message.answer("👤 Yangi <b>Familiya Ism Sharifni</b> kiriting:", parse_mode="HTML")
    elif choice == "mfy":
        await state.set_state(FormState.waiting_for_mfy)
        await callback.message.answer("🏢 Yangi <b>MFY</b> tanlang:", reply_markup=get_mfy_inline_keyboard())
    elif choice == "sana":
        await state.set_state(FormState.waiting_for_sana)
        await callback.message.answer("📅 Yangi <b>Sana</b> kiriting:", parse_mode="HTML")
    elif choice == "photos":
        await state.update_data(photos=[])
        await callback.message.answer("📸 Oldingi rasmlar o'chirildi. \nYangi <b>1-10 ta rasm</b> yuboring:", parse_mode="HTML")


# Guruh va Google Sheetsga yuborish
@form_router.callback_query(FormState.waiting_for_photos, F.data == "form:submit")
async def process_submit(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🚀 Yuborilmoqda...")
    data = await state.get_data()
    photos = data.get("photos", [])

    if not photos:
        await callback.answer("❌ Kamida 1 ta rasm shart!", show_alert=True)
        return

    # Yuborilganini anniq vaqti
    sent_timestamp = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")

    # Birinchi guruhga yuborib message_id olinadi
    report_text = build_preview_text(data)
    sent_message = None

    try:
        media = []
        for i, item in enumerate(photos):
            if i == 0:
                if item["type"] == "photo":
                    media_obj = InputMediaPhoto(
                        media=item["id"],
                        caption=report_text,
                        parse_mode="HTML"
                    )
                else:
                    media_obj = InputMediaDocument(
                        media=item["id"],
                        caption=report_text,
                        parse_mode="HTML"
                    )
            else:
                if item["type"] == "photo":
                    media_obj = InputMediaPhoto(media=item["id"])
                else:
                    media_obj = InputMediaDocument(media=item["id"])

            media.append(media_obj)

        # 📤 Guruhga yuborish (1-10 ta uchun send_media_group ishlaydi)
        sent_messages_list = await callback.bot.send_media_group(
            chat_id=CHAT_TARGET,
            message_thread_id=TOPIC_ID if TOPIC_ID else None,
            media=media
        )
        sent_message = sent_messages_list[0]

    except TelegramBadRequest as e:
        logger.error(f"TelegramBadRequest: {e}")
        await callback.message.answer(f"❌ Guruh xatolik: {e}")
        return

    # Post_url ni xosil qilish
    sent_msg_id = sent_message.message_id if sent_message else None
    post_url = ""
    if sent_message:
        if CHAT_TARGET < 0:
            chat_id_clean = str(CHAT_TARGET).replace("-100", "")
            if TOPIC_ID:
                # Forum/topicli guruh
                post_url = f"https://t.me/c/{chat_id_clean}/topic/{TOPIC_ID}/{sent_message.message_id}"
            else:
                # Oddiy guruh
                post_url = f"https://t.me/c/{chat_id_clean}/{sent_message.message_id}"
        else:
            # Shaxsiy chat
            if callback.from_user.username:
                post_url = f"https://t.me/{callback.from_user.username}/{sent_message.message_id}"


    # Google Sheetsga yozish
    try:
        # tg_link = f"https://t.me/{callback.from_user.username}" if callback.from_user.username else f"tg://user?id={callback.from_user.id}"
        tg_link = ""

        if callback.from_user:
            # 1. Если у пользователя есть @username
            if callback.from_user.username:
                full_name = (callback.from_user.full_name or "Ismi yoʻq").replace('"', '""')
                tg_link = f'=HYPERLINK("https://t.me/{callback.from_user.username}"; "{full_name}")'

            # 2. Если у пользователя нет username (ссылка по ID)
            else:
                tg_link = f'=HYPERLINK("tg://user?id={callback.from_user.id}"; "ID: {callback.from_user.id}")'

        row_number = await append_message(
            extracted_number=int(data['id']),
            message_text=f"{data['fish']} | {data['mfy']} | {data['sana']}",
            tg_link=tg_link,
            post_url=post_url,
            sent_timestamp=sent_timestamp,
            message_id=sent_msg_id,
            chat_id=CHAT_TARGET
        )

        # message_id va chat_id saqlash
        if sent_message and row_number:
            # await update_message_ids(
            #     row_number=row_number,
            #     message_id=sent_msg_id,
            #     chat_id=CHAT_TARGET
            # )

            mapping = load_mapping()
            mapping[get_mapping_key(CHAT_TARGET, sent_msg_id)] = row_number
            save_mapping(mapping)

    except Exception as e:
        logger.error(f"Noma'lum xatolik send_media_group da: {type(e).__name__}: {e}", exc_info=True)
        await callback.message.answer(f"❌ Kutilmagan xatolik: {type(e).__name__}")
        return

    try:
        # 1. Inline tugmali preview xabarni o'chirish
        await callback.message.delete()
    except Exception:
        pass

    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text = "🎉 <b>Ma'lumotlaringiz muvaffaqiyatli yuborildi!</b>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


# ❓ Инструкция
@form_router.message(F.text == "❓ Yo'riqnoma")
async def show_help(message: Message):
    help_text = (
        "📖 <b>Botdan foydalanish bo'yicha ko'rsatmalar</b>\n\n"
        "🔹 <b>📝 Formani to'ldirish</b> — yangi ariza boshlash\n"
        "🔹 <b>🔙 Menyuga qaytish</b> — formani bekor qilish va bosh menyuga qaytish\n"
        "🔹 <b>✏️ Tahrirlash</b> — yuborishdan oldin istalgan maydonni o'zgartirish\n"
        "🔹 <b>✅ Yuborish</b> — ma'lumotlarni tasdiqlash hamda guruh va jadvalga yuborish\n\n"
        "📸 <b>Rasmga qo'yiladigan talablar:</b>\n"
        "• Format: JPG / JPEG, PNG, WEBP, BMP / TIFF / HEIC \n"
        "• Soni: 1 tadan 10 tagacha\n\n"
        "❓ <b>Muammo yuzasidan:</b> Administratorga yozing."
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())


# Bekor qilish
@form_router.message(F.text == "🔙 Bekor qilish")
@form_router.callback_query(F.data == "cancel")
async def cancel_form(message: Message | CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("⚠️ Faol forma topilmadi.", reply_markup=get_main_keyboard())
        return

    await state.clear()
    if isinstance(message, CallbackQuery):
        await message.message.delete()
        await message.answer("❌ Forma bekor qilindi.", reply_markup=get_main_keyboard())
    else:
        await message.answer("❌ Forma bekor qilindi.", reply_markup=get_main_keyboard())