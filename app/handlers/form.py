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
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.exceptions import TelegramBadRequest

from app.sheets import append_message, update_message_ids
from app.config import CHAT_TARGET, TOPIC_ID
from app.regex_utils import extract_numbers

form_router = Router()

# Bosqichalar
class FormState(StatesGroup):
    waiting_for_id = State()
    waiting_for_fish = State()
    waiting_for_mfy = State()
    waiting_for_sana = State()
    waiting_for_photos = State()

# Albom IDsi, span qilmasligi uchun
ALBUM_LOCKS = set()

# MFY ro'yxati
MFY_OPTIONS = {
    "Адиробод МФЙ": "01",
    "Андижон МФЙ": "02",
    "Дўстлик МФЙ": "03",
    "Ёшлик МФЙ": "04",
    "Лалмикор МФЙ": "05",
    "Мустақиллик МФЙ": "06",
    "Навбаҳор МФЙ": "07",
    "Навоий МФЙ": "08",
    "Наврўз МФЙ": "09",
    "Нурафшон МФЙ": "10",
    "Нуробод МФЙ": "11",
    "Ойбек МФЙ": "12",
    "Оқар МФЙ": "13",
    "Оқбулоқ МФЙ": "14",
    "Равот МФЙ": "15",
    "Тараққиёт МФЙ": "16",
    "Тинчлик МФЙ": "17",
    "Тошкесган МФЙ": "18",
    "Шарқ Юлдузи МФЙ": "19",
    "Шодлик МФЙ": "20",
    "Янгиҳаёт МФЙ": "21",
    "Янгикент МФЙ": "22",
    "Янгиобод МФЙ": "23"
}

MAPPING_FILE = "message_mapping.json"

# MFYlarni klaviaturadagi knopkalari
def get_mfy_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    #Xar bir MFY knopkalarini yaratadigan sikl
    for name, value in MFY_OPTIONS.items():
        builder.add(InlineKeyboardButton(text=name, callback_data=f"mfy:{value}"))

    #Knopkalarni ustunlar bilan ko'rsatadi
    builder.adjust(2)

    #Orqaga knopkasini ohiriga qo'shadi
    builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="mfy:back"))

    return builder.as_markup()


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
@form_router.message(F.text == "/form")
async def start_form(message: Message, state: FSMContext):
    # Vaqtincha xotirani tozalash
    await state.clear()

    # ID handleriga o'tadi
    await state.set_state(FormState.waiting_for_id)
    await message.answer(
        "1️⃣ <b>ID</b> raqamini kiriting:",
        parse_mode="HTML"
    )


# ID handleri
@form_router.message(FormState.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    extracted = extract_numbers(message.text)

    # Son yo'qligiga tekshiruv
    if not extracted:
        await message.answer("❌ ID notog'ri kiritilgan:")
        return

    # IDni vaqtincha xotirada saqlab turadi
    await state.update_data(id=extracted)
    data = await state.get_data()

    # Agar editing rejimida bo'lsa -> Previewga qaytish
    if data.get("is_editing"):
        await state.update_data(is_editing=False)
        await state.set_state(FormState.waiting_for_photos)
        text = build_preview_text({**data, "id": extracted})
        msg = await message.answer(text, parse_mode="HTML", reply_markup=get_submit_keyboard())
        await state.update_data(last_msg_id=msg.message_id)
        return

    # FISH handleriga o'tadi
    await state.set_state(FormState.waiting_for_fish)
    await message.answer(
        f"✅ ID: <code>{extracted}</code>\n\n"
        "2️⃣ <b>F.I.Sh.</b> (Familiya Ism Sharif) ni kiriting:",
        parse_mode="HTML"
    )


# F.I.Sh. handleri
@form_router.message(FormState.waiting_for_fish)
async def process_fish(message: Message, state: FSMContext):
    fish = message.text.strip()

    # FISHni to'liq yozilganini tekshiradi
    # if len(fish) < 3:
    #     await message.answer("❌ FISH to'liq kiriting:")
    #     return

    #FISHni vaqtincha xotiraga saqlab turadi
    await state.update_data(fish=fish)
    data = await state.get_data()

    # Agar editing rejimida bo'lsa -> Previewga qaytish
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
        "3️⃣ <b>MFY</b> ni tanlang:",
        parse_mode="HTML",
        reply_markup=get_mfy_keyboard()
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
            parse_mode="HTML"
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
        "4️⃣ <b>Sana</b> ni kiriting (masalan: 07.05.2026):",
        parse_mode="HTML",
        reply_markup=None
    )

# Sana handleri
@form_router.message(FormState.waiting_for_sana)
async def process_sana(message: Message, state: FSMContext):
    sana = message.text.strip()

    # Validatsiya: 1 va undan ko'p probel/to'chka/defis ishlatsa bo'ladi
    if not re.match(r"\d{1,2}[\s./-]+\d{1,2}[\s./-]+\d{2,4}$", sana):
        await message.answer(
            "❌ Sanani to'g'ri formatda kiriting(masalan 07.05.20026:):"
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
        "5️⃣ <b>1-10 ta rasm</b> yuboring:\n"
        "✅ Tayyor bo'lgach joylash tugmasini bosing.",
        parse_mode="HTML"
    )


# Photo handleri
@form_router.message(FormState.waiting_for_photos, F.photo)
async def process_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    # Limitdan oshmaganini tekshirish
    if len(photos) >= 10:
        if message.media_group_id not in ALBUM_LOCKS:
            ALBUM_LOCKS.add(message.media_group_id)
            await message.answer("⚠️ Maksimum 10 ta rasim qabul qilinadi")
        return

    # Rasm qo'shish
    photo_file_id = message.photo[-1].file_id
    photos.append(photo_file_id)
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

    # # Bitta rasm yuborilganda darrov javob beradi
    # if not message.media_group_id:
    #     await message.answer(
    #         f"📸 {len(photos)} ta rasm qabul qilindi. Davom eting yoki yuborishni bosing."
    #     )
    #     return
    #
    # # Albom yubirlganda mikro-pauza bo'lib xamma rasmni kutadi
    # if message.media_group_id not in ALBUM_LOCKS:
    #     ALBUM_LOCKS.add(message.media_group_id)
    #     await asyncio.sleep(0.5)
    #
    #     current_data = await state.get_data()
    #     current_photos = current_data.get("photos", [])
    #
    #     await message.answer(
    #         f"📸 {len(current_photos)} ta rasm qabul qilindi. Davom eting yoki yuborishni bosing."
    #     )
    #
    #     # Vaqtinchalik royhatni tozalash
    #     ALBUM_LOCKS.discard(message.media_group_id)


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
        await callback.message.answer("👤 Yangi <b>F.I.Sh.</b> kiriting:", parse_mode="HTML")
    elif choice == "mfy":
        await state.set_state(FormState.waiting_for_mfy)
        await callback.message.answer("🏢 Yangi <b>MFY</b> tanlang:", reply_markup=get_mfy_keyboard())
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
    sent_timestamp = datetime.now(timezone.utc).astimezone().isoformat()

    # Birinchi guruhga yuborib message_id olinadi
    report_text = build_preview_text(data)
    sent_message = None

    try:
        if len(photos) == 1:
            sent_message = await callback.bot.send_photo(
                chat_id=CHAT_TARGET,
                message_thread_id=TOPIC_ID if TOPIC_ID else None,
                photo=photos[0],
                caption=report_text,
                parse_mode="HTML"
            )
        else:
            media = [InputMediaPhoto(media=photos[0], caption=report_text, parse_mode="HTML")]
            media += [InputMediaPhoto(media=p) for p in photos[1:]]
            sent_messages_list = await callback.bot.send_media_group(
                chat_id=CHAT_TARGET,
                message_thread_id=TOPIC_ID if TOPIC_ID else None,
                media=media
            )
            sent_message = sent_messages_list[0]
    except TelegramBadRequest as e:
        await callback.message.answer(f"❌ Gurug xatolik: {e}")
        return

    # Post_url ni xosil qilish
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
        tg_link = f"https://t.me/{callback.from_user.username}" if callback.from_user.username else f"tg://user?id={callback.from_user.id}"
        row_number = await append_message(
            extracted_number=int(data['id']),
            message_text=f"{data['fish']} | {data['mfy']} | {data['sana']}",
            message_date=data['sana'],
            tg_link=tg_link,
            post_url=post_url,
            sent_timestamp=sent_timestamp
        )

        # message_id va chat_id saqlash
        if sent_message and row_number:
            await update_message_ids(
                row_number=row_number,
                message_id=sent_message.message_id,
                chat_id=CHAT_TARGET
            )

            mapping = load_mapping()
            mapping[get_mapping_key(CHAT_TARGET, sent_message.message_id)] = row_number
            save_mapping(mapping)

    except Exception as e:
        await callback.message.answer(f"⚠️ Sheets xatolik: {e}")

    await callback.message.edit_text(
        "🎉 <b>Ma'lumotlaringiz muvaffaqiyatli yuborildi!</b>",
        parse_mode="HTML"
    )
    await state.clear()


# Bekor qilish
@form_router.message(F.text == "/cancel")
@form_router.callback_query(F.data == "cancel")
async def cancel_form(message: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    if isinstance(message, CallbackQuery):
        await message.message.delete()
        await message.answer("❌ Forma bekor qilindi.")
    else:
        await message.answer("❌ Forma bekor qilindi.", reply_markup=None)
