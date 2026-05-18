from datetime import datetime, timezone
import os
import gspread_asyncio
from _testcapi import awaitType
from google.auth import aws
from google.oauth2.service_account import Credentials
from app.config import SHEET_NAME

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
        message_date: str,
        tg_link: str,
        post_url: str = "",
        sent_timestamp: str =None
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
        sent_timestamp = datetime.now(timezone.utc).astimezone().isoformat()

    headers = await sheet.row_values(1)
    expected_headers = ["ID", "FISH_MFY_SANA", "Sana", "TG_link", "Post_URL", "Sent_Timestamp", "Message_ID", "Chat_ID"]

    if not headers or headers[0] != "ID":
        await sheet.append_row(expected_headers)
        headers = expected_headers

    await sheet.append_row([
        extracted_number,
        message_text,
        message_date,
        tg_link,
        post_url,
        sent_timestamp,
        "",
        ""
    ])

    return await sheet.row_count

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
        message_date: str = None,
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

    # Faqat berilgan qatorni yangilash
    if extracted_number is not None:
        current[0] = str(extracted_number)
    if message_text is not None:
        current[1] = message_text
    if message_date is not None:
        current[2] = message_date
    if tg_link is not None:
        current[3] = tg_link
    if post_url is not None:
        current[4] = post_url

    await sheet.update(f"A{row_number}:F{row_number}", [current[:6]])

# Qatorni message_ig va chat_id bo'yicha o'chirish
async def delete_row_by_message_id(message_id: int, chat_id: int):
    row_num = await find_row_by_message_id(message_id, chat_id)
    if row_num:
        client = await client_manager.authorize()
        spreadsheet = await client.open(SHEET_NAME)
        sheet = await spreadsheet.get_worksheet(0)
        await sheet.delete_rows(row_num, row_num)
        return True
    return False

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

