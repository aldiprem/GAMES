import os
from dotenv import load_dotenv

load_dotenv()

# Database paths
DB_PATH = os.path.join(os.path.dirname(__file__), 'database')
os.makedirs(DB_PATH, exist_ok=True)

# Owner IDs yang diizinkan akses panel
ALLOWED_OWNER_IDS = [7998861975]  # Tambahkan ID owner lain jika perlu

# Flask config
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
PORT = 8000
HOST = '0.0.0.0'

# Database files
USERS_DB = os.path.join(DB_PATH, 'users.db')
STOK_DB = os.path.join(DB_PATH, 'stok.db')
BOTS_DB = os.path.join(DB_PATH, 'bots.db')  # Sama dengan username.db di b.py
