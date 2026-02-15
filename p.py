import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import os
from dotenv import load_dotenv
import asyncio

# ============= LOAD ENV =============
load_dotenv()

API_ID = int(os.getenv("API_ID"))   # HARUS INT
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_PORT = int(os.getenv("API_PORT", 5000))
DB_PATH = "giveaway.db"

# ============= DATABASE INIT =============
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

# ============= DATABASE FUNCTIONS =============
def get_total_users():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

def get_users_today():
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at)=DATE(?)", (today,))
    return cur.fetchone()[0]

def get_recent_users(limit=5):
    cur.execute("""
        SELECT user_id, fullname, username, joined_at
        FROM users
        ORDER BY joined_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()

    return [
        {
            "user_id": r[0],
            "fullname": r[1],
            "username": r[2],
            "joined_at": r[3]
        }
        for r in rows
    ]

# ============= FLASK API =============
app = Flask(__name__)

CORS(app,
     origins=["https://aldiprem.github.io"],
     methods=["GET", "OPTIONS"],
     allow_headers=["Content-Type"],
     supports_credentials=True)

@app.route("/api/stats")
def stats_api():
    try:
        return jsonify({
            "success": True,
            "total_users": get_total_users(),
            "users_today": get_users_today(),
            "recent_users": get_recent_users(),
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "time": datetime.now().isoformat()
    })

def run_flask():
    app.run(host="0.0.0.0", port=API_PORT, debug=False)

# ============= TELEGRAM BOT =============
bot = TelegramClient("bot", API_ID, API_HASH)

@bot.on(events.NewMessage(pattern="^/start$"))
async def start(event):
    user = await event.get_sender()

    user_id = user.id
    fullname = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    username = user.username or ""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert user jika belum ada
    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, fullname, username, joined_at, first_start, last_start)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, fullname, username, now, now, now))

    # Update last_start
    cur.execute("""
        UPDATE users SET last_start=? WHERE user_id=?
    """, (now, user_id))

    conn.commit()

    total = get_total_users()

    await event.respond(f"""
🎁 **Halo {fullname}!**

✅ Anda sudah tercatat di database.
👥 Total Pengguna: {total}

📊 Statistik:
https://aldiprem.github.io/GAMES/
""")

@bot.on(events.NewMessage(pattern="^/stats$"))
async def stats_cmd(event):
    await event.respond(f"""
📊 **STATISTIK BOT**

👥 Total User: {get_total_users()}
📅 Hari Ini: {get_users_today()}

🌐 Website:
https://aldiprem.github.io/GAMES/
""")

# ============= MAIN =============
async def main():
    await bot.start(bot_token=BOT_TOKEN)

    print("✅ Bot berjalan")
    print(f"🌐 API: http://0.0.0.0:{API_PORT}")

    await bot.run_until_disconnected()

if __name__ == "__main__":
    # Jalankan Flask di thread
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 Flask API started")

    asyncio.run(main())
