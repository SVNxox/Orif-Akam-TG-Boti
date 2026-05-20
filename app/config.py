import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

SHEET_NAME = os.getenv("SHEET_NAME")

CHAT_TARGET = int(os.getenv("CHAT_TARGET"))
TOPIC_ID = int(os.getenv("TOPIC_ID"))

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "/etc/letsencrypt/live/orifjon-tgbot.duckdns.org/fullchain.pem")
SSL_KEY_PATH = os.getenv("SSL_KEY_PATH", "/etc/letsencrypt/live/orifjon-tgbot.duckdns.org/privkey.pem")