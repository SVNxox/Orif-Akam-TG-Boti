import os
from dotenv import load_dotenv
import gspread_asyncio
from google.oauth2.service_account import Credentials

load_dotenv()

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


SHEET_NAME = os.getenv("SHEET_NAME")

async def append_number(
        extracted_number: str,
):
    if not SHEET_NAME:
        raise ValueError(".env faylda SHEET_NAME berilmagan")

    if not extracted_number or not extracted_number.isdigit():
        return

    client = await client_manager.authorize()
    spreadsheet = await client.open(SHEET_NAME)
    sheet = await spreadsheet.get_worksheet(0)

    existing = await sheet.col_values(1)

    if extracted_number in existing:
        return

    await sheet.append_row([extracted_number])