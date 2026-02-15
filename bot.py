import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# ============= KONFIGURASI =============
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_PATH = 'giveaway.db'
API_PORT = int(os.getenv('API_PORT', 5000))

# ============= INISIALISASI DATABASE =============
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    fullname TEXT,
    username TEXT,
    joined_at TEXT,
    first_start TEXT,
    last_start TEXT,
    last_nego INTEGER DEFAULT 0
)
""")
conn.commit()

# ============= FUNGSI DATABASE =============
def get_total_users():
    """Mengambil total jumlah user"""
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

def get_users_today():
    """Mengambil jumlah user yang join hari ini"""
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE(?)", (today,))
    return cur.fetchone()[0]

def get_recent_users(limit=5):
    """Mengambil user terbaru"""
    cur.execute("""
        SELECT user_id, fullname, username, joined_at 
        FROM users 
        ORDER BY joined_at DESC 
        LIMIT ?
    """, (limit,))
    users = cur.fetchall()
    
    result = []
    for user in users:
        result.append({
            'user_id': user[0],
            'fullname': user[1],
            'username': user[2],
            'joined_at': user[3]
        })
    return result

app = Flask(__name__)
CORS(app)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Endpoint API untuk mengambil statistik"""
    try:
        total_users = get_total_users()
        users_today = get_users_today()
        recent_users = get_recent_users()
        
        return jsonify({
            'success': True,
            'total_users': total_users,
            'users_today': users_today,
            'recent_users': recent_users,
            'last_updated': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint untuk mengecek kesehatan server"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

def run_flask():
    """Menjalankan Flask server di thread terpisah"""
    app.run(host='0.0.0.0', port=API_PORT, debug=False, threaded=True)

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    user = event.sender
    user_id = user.id
    fullname = user.first_name or ""
    if user.last_name:
        fullname += f" {user.last_name}"

    username = None
    if user.username:
        username = user.username
    elif getattr(user, "usernames", None):
        username = user.usernames[0].username

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insert atau ignore jika sudah ada
    cur.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, fullname, username, joined_at, first_start, last_start) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, fullname, username, now, now, now))
    
    # Update last_start jika user sudah ada
    cur.execute("""
        UPDATE users 
        SET last_start = ? 
        WHERE user_id = ? AND last_start < ?
    """, (now, user_id, now))
    
    conn.commit()

    total_users = get_total_users()
    
    msg = f"""
🎁 **Hallo {fullname}!**

✅ Anda telah tercatat dalam database!
👥 **Total Pengguna:** {total_users}

📊 Lihat statistik di: https://username.github.io/repository-anda/
    """

    await event.respond(msg)

@bot.on(events.NewMessage(pattern="^/stats$"))
async def stats(event):
    """Command untuk melihat statistik"""
    total_users = get_total_users()
    users_today = get_users_today()
    
    msg = f"""
📊 **STATISTIK BOT**

👥 **Total Pengguna:** {total_users}
📅 **Pengguna Hari Ini:** {users_today}
📈 **Website:** https://username.github.io/repository-anda/
    """
    
    await event.respond(msg)

async def main():
    print(f"✅ Bot berjalan!")
    print(f"📊 API Server: http://207.180.194.191:{API_PORT}")
    print(f"🌐 Website: https://username.github.io/repository-anda/")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🚀 Flask API server dimulai...")
    
    # Jalankan bot
    print("🤖 Telegram bot dimulai...")
    bot.loop.run_until_complete(main())
