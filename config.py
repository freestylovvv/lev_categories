import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_GROUP_ID = int(os.getenv("SOURCE_GROUP_ID", "0"))
CATALOG_CHANNEL_ID = int(os.getenv("CATALOG_CHANNEL_ID", "0"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]