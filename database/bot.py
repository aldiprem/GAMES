import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'bots.db')

def init_database():
    """Inisialisasi database bots (sama dengan username.db)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_id TEXT NOT NULL,
            api_hash TEXT NOT NULL,
            bot_token TEXT NOT NULL UNIQUE,
            username TEXT,
            bot_id TEXT,
            is_main BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'active',
            last_active TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cek main bot
    cursor.execute("SELECT COUNT(*) FROM bots WHERE is_main = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO bots (api_id, api_hash, bot_token, is_main) 
            VALUES (?, ?, ?, 1)
        ''', ('24576633', '29931cf620fad738ee7f69442c98e2ee', '7277244478:AAGZwGYXxzG-6JaxYpTVPt5TbbEKVbwn-FM'))
    
    conn.commit()
    conn.close()

def load_bot_configs():
    """Load semua konfigurasi bot"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT api_id, api_hash, bot_token, username, bot_id, is_main FROM bots WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    
    configs = []
    for row in rows:
        configs.append({
            'api_id': row[0],
            'api_hash': row[1],
            'bot_token': row[2],
            'username': row[3],
            'bot_id': row[4],
            'is_main': row[5] == 1
        })
    return configs

def get_main_bot():
    """Ambil main bot config"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT api_id, api_hash, bot_token FROM bots WHERE is_main = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'api_id': row[0],
            'api_hash': row[1],
            'bot_token': row[2]
        }
    return None

def save_bot(api_id, api_hash, bot_token, is_main=False):
    """Simpan bot baru"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO bots (api_id, api_hash, bot_token, is_main) 
            VALUES (?, ?, ?, ?)
        ''', (api_id, api_hash, bot_token, 1 if is_main else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_bot_info(bot_token, username, bot_id):
    """Update info bot"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE bots 
        SET username = ?, bot_id = ?, last_active = CURRENT_TIMESTAMP
        WHERE bot_token = ?
    ''', (username, bot_id, bot_token))
    conn.commit()
    conn.close()

def get_all_bots():
    """Ambil semua bot dengan detail"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM bots 
        ORDER BY is_main DESC, created_at DESC
    ''')
    bots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return bots

def delete_bot(bot_token):
    """Hapus bot (soft delete)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_main FROM bots WHERE bot_token = ?", (bot_token,))
    result = cursor.fetchone()
    
    if result and result[0] == 1:
        conn.close()
        return False
    
    cursor.execute("DELETE FROM bots WHERE bot_token = ?", (bot_token,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_bot_stats():
    """Ambil statistik bot"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM bots")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bots WHERE is_main = 1")
    main = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bots WHERE is_main = 0")
    clone = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'main': main,
        'clone': clone
    }

# Initialize database
init_database()
