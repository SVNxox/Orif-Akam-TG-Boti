from datetime import datetime, timezone
import os
import gspread_asyncio
from google.oauth2.service_account import Credentials
from app.config import SHEET_NAME
from zoneinfo import ZoneInfo

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_credentials():
    return Credentials.from_service_account_file(
        "credentials.json",
        scopes=SCOPES,
    )

client_manager = gspread_asyncio.AsyncioGspreadClientManager(get_credentials)


async def append_message(
        extracted_number: int,
        message_text: str,
        tg_link: str,
        post_url: str = "",
        sent_timestamp: str = None,
        message_id: int = None,
        chat_id: int = None
):
    if not SHEET_NAME:
        raise ValueError(".env faylda SHEET_NAME berilmagan")
    #
    # if not extracted_number:
    #     return

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    # existing = await sheet.col_values(1)
    #
    # if extracted_number in existing:
    #     return

    if sent_timestamp is None:
        sent_timestamp = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")

    headers = await sheet.row_values(1)
    expected_headers = ["ID", "FISH_MFY_SANA", "Yuboruvchi_profili", "Post_URL_manzili", "Yuborilgan_sana_va_vaqt", "Message_ID", "Chat_ID"]

    if not headers or headers[0] != "ID":
        await sheet.append_row(expected_headers)
        headers = expected_headers

    await sheet.append_row(
        [
            extracted_number,
            message_text,
            tg_link,
            post_url,
            sent_timestamp,
            str(message_id) if message_id else "",
            str(chat_id) if chat_id else ""
        ],
        value_input_option='USER_ENTERED'
    )

    return sheet.row_count

# Xabar qatorini message_id bo'yicha topish
async def find_row_by_message_id(message_id: int, chat_id: int):
    if not SHEET_NAME:
        return None

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    # Barcha ma'lumotlarni olish
    all_values = await sheet.get_values()

    # Qatorni topish
    if not all_values:
        return None

    headers = all_values[0]

    try:
        msg_id_col = headers.index("Message_ID") + 1
        chat_id_col = headers.index("Chat_ID") + 1
    except ValueError:
        return None

    for idx, row in enumerate(all_values[1:], start=2):
        if len(row) >= max(msg_id_col, chat_id_col):
            if str(row[msg_id_col - 1]) == str(message_id) and str(row[chat_id_col - 1]) == str(chat_id):
                return idx

    return None

# Berilgan qatorni yangilash
async def update_row_by_id(
        row_number: int,
        extracted_number: int = None,
        message_text: str = None,
        tg_link: str = None,
        post_url: str = None
):
    if not SHEET_NAME or not row_number:
        return

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    # Qatorni qiymatini olish
    current = await sheet.row_values(row_number)

    while len(current) < 6:
        current.append("")

    # Faqat berilgan qatorni yangilash
    if extracted_number is not None:
        current[0] = int(extracted_number)
    if message_text is not None:
        current[1] = message_text
    if tg_link is not None:
        current[2] = tg_link
    if post_url is not None:
        current[3] = post_url

    await sheet.update(f"A{row_number}:F{row_number}", [current[:5]], value_input_option='USER_ENTERED')

# Qatorni message_ig va chat_id bo'yicha o'chirish
# app/sheets.py - добавьте, если отсутствует

async def delete_row_by_message_id(message_id: int, chat_id: int):
    """
    Находит и удаляет строку по message_id + chat_id.
    Google Sheets автоматически сдвигает строки вверх после удаления.
    Возвращает True если удалено, False если не найдено.
    """
    if not SHEET_NAME:
        return False

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    row_num = await find_row_by_message_id(message_id, chat_id)
    if not row_num:
        return False

    await sheet.delete_rows(row_num, row_num)
    return True

# Sinxronizatsiya uchun message_id va chat_id qatorga saqlash
async def update_message_ids(row_number: int, message_id: int, chat_id: int):
    if not SHEET_NAME or not row_number:
        return

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    # G va H (7 va 8) ustunlarni yangilash
    await sheet.update_cell(row_number, 7, str(message_id))
    await sheet.update_cell(row_number, 8, str(chat_id))


async def update_row_by_message_id(
        message_id: int,
        chat_id: int,
        message_text: str = None,
        extracted_number: int = None,
):
    """
    Находит строку по message_id + chat_id и обновляет указанные поля.
    Возвращает True если строка найдена и обновлена, False если не найдена.
    """
    if not SHEET_NAME:
        return False

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    # Находим номер строки
    row_num = await find_row_by_message_id(message_id, chat_id)
    if not row_num:
        return False

    updates = []

    # Колонка A (ID) — индекс 1
    if extracted_number is not None:
        await sheet.update_cell(row_num, 1, str(extracted_number))

    # Колонка B (FISH_MFY_SANA) — индекс 2
    if message_text is not None:
        await sheet.update_cell(row_num, 2, message_text)

    return True