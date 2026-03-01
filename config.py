import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), 'database')
os.makedirs(DB_PATH, exist_ok=True)

OWNER_IDS_STR = os.getenv('OWNER_IDS', '7998861975')
ALLOWED_OWNER_IDS = [int(id.strip()) for id in OWNER_IDS_STR.split(',')]

# Flask config
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
PORT = int(os.getenv('FLASK_PORT', 8000))
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Database files
USERS_DB = os.path.join(DB_PATH, 'users.db')
STOK_DB = os.path.join(DB_PATH, 'stok.db')
BOTS_DB = os.path.join(DB_PATH, 'bots.db')
GACHA_DB = os.path.join(DB_PATH, 'gacha.db')

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH')

# Website URL
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:8000')

# Validate required configs
if not all([BOT_TOKEN, BOT_USERNAME, API_ID, API_HASH]):
    print("⚠️  Warning: Beberapa konfigurasi bot tidak lengkap di .env")
