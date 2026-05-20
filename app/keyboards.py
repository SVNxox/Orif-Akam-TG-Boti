# app/keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ─────────────────────────────────────────────
# 🎯 Главное меню (ReplyKeyboard)
# ─────────────────────────────────────────────
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с основными командами — видна всегда, когда не заполняется форма"""
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="📝 Formani to'ldirish"))
    builder.add(KeyboardButton(text="❓ Yo'riqnoma"))

    builder.adjust(1)  # Кнопки в 1 колонку
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


# ─────────────────────────────────────────────
# ↩️ Клавиатура «Назад» (для формы)
# ─────────────────────────────────────────────
def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Простая кнопка «Назад» — появляется при заполнении формы"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Orqaga"))
    builder.add(KeyboardButton(text="🔙 Menyuga qaytish"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─────────────────────────────────────────────
# 🎯 Inline-кнопки (для превью формы)
# ─────────────────────────────────────────────
def get_submit_keyboard() -> InlineKeyboardMarkup:
    """Кнопки «Отправить» и «Редактировать» под превью"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="form:submit"),
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="form:edit_menu"),
    )
    return builder.as_markup()


def get_edit_fields_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора поля для редактирования"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔢 ID", callback_data="edit:id"),
        InlineKeyboardButton(text="👤 F.I.Sh.", callback_data="edit:fish"),
    )
    builder.row(
        InlineKeyboardButton(text="🏢 MFY", callback_data="edit:mfy"),
        InlineKeyboardButton(text="📅 Sana", callback_data="edit:sana"),
    )
    builder.row(InlineKeyboardButton(text="📸 Rasm", callback_data="edit:photos"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="edit:cancel"))
    return builder.as_markup()


def get_mfy_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопки для выбора МФЙ"""
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

    builder = InlineKeyboardBuilder()
    for name, value in MFY_OPTIONS.items():
        builder.add(InlineKeyboardButton(text=name, callback_data=f"mfy:{value}"))
    builder.adjust(2)
    return builder.as_markup()