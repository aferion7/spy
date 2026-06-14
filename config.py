import os
from dotenv import load_dotenv

load_dotenv()

API_ID = None
API_HASH = None
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
SESSION_STRING = None
