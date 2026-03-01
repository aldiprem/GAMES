import sqlite3
import os
from datetime import datetime
import config

DB_PATH = config.GACHA_DB

def init_database():
    """Inisialisasi database gacha"""
    try:
        # Pastikan direktori database ada
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabel deposit transactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposit_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                charge_id TEXT UNIQUE,
                payload TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                product_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Tabel gacha history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gacha_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                price INTEGER,
                status TEXT DEFAULT 'available',
                purchased_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabel user profiles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                total_deposit INTEGER DEFAULT 0,
                total_gacha INTEGER DEFAULT 0,
                last_deposit TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Database gacha initialized at {DB_PATH}")
    except Exception as e:
        print(f"❌ Error initializing gacha database: {e}")

def add_deposit_transaction(user_id, amount, payload, product_id='gacha_deposit'):
    """Tambah transaksi deposit baru"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert transaksi
        cursor.execute('''
            INSERT INTO deposit_transactions (user_id, amount, payload, product_id, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (user_id, amount, payload, product_id))
        
        trans_id = cursor.lastrowid
        
        # Update atau insert user profile
        cursor.execute('''
            INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return trans_id
    except sqlite3.IntegrityError:
        print(f"Duplicate payload: {payload}")
        return None
    except Exception as e:
        print(f"Error add_deposit_transaction: {e}")
        return None

def complete_deposit_transaction(charge_id, payload):
    """Selesaikan transaksi deposit"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Cek transaksi pending
        cursor.execute('''
            SELECT user_id, amount FROM deposit_transactions 
            WHERE payload = ? AND status = 'pending'
        ''', (payload,))
        trans = cursor.fetchone()
        
        if not trans:
            print(f"Transaction not found: {payload}")
            conn.close()
            return False
        
        user_id, amount = trans
        
        # Update transaksi
        cursor.execute('''
            UPDATE deposit_transactions 
            SET status = 'completed', charge_id = ?, completed_at = CURRENT_TIMESTAMP
            WHERE payload = ?
        ''', (charge_id, payload))
        
        # Update user profile
        cursor.execute('''
            UPDATE user_profiles 
            SET total_deposit = total_deposit + ?, last_deposit = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (amount, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error complete_deposit_transaction: {e}")
        return False

def get_user_gacha_profile(user_id):
    """Ambil profile gacha user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ambil profile
        cursor.execute('''
            SELECT * FROM user_profiles WHERE user_id = ?
        ''', (user_id,))
        profile = cursor.fetchone()
        
        # Jika tidak ada, buat baru
        if not profile:
            cursor.execute('''
                INSERT INTO user_profiles (user_id) VALUES (?)
            ''', (user_id,))
            conn.commit()
            
            cursor.execute('''
                SELECT * FROM user_profiles WHERE user_id = ?
            ''', (user_id,))
            profile = cursor.fetchone()
        
        # Ambil deposit terakhir
        cursor.execute('''
            SELECT * FROM deposit_transactions 
            WHERE user_id = ? AND status = 'completed'
            ORDER BY created_at DESC LIMIT 5
        ''', (user_id,))
        deposits = [dict(row) for row in cursor.fetchall()]
        
        result = dict(profile) if profile else {
            'user_id': user_id,
            'total_deposit': 0,
            'total_gacha': 0
        }
        result['deposits'] = deposits
        
        conn.close()
        return result
    except Exception as e:
        print(f"Error get_user_gacha_profile: {e}")
        return {
            'user_id': user_id,
            'total_deposit': 0,
            'total_gacha': 0,
            'deposits': []
        }

def get_pending_deposit(payload):
    """Ambil transaksi deposit pending berdasarkan payload"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM deposit_transactions 
            WHERE payload = ? AND status = 'pending'
        ''', (payload,))
        trans = cursor.fetchone()
        
        conn.close()
        return dict(trans) if trans else None
    except Exception as e:
        print(f"Error get_pending_deposit: {e}")
        return None

def add_gacha_purchase(user_id, username, price):
    """Catat pembelian gacha"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert history
        cursor.execute('''
            INSERT INTO gacha_history (user_id, username, price, status, purchased_at)
            VALUES (?, ?, ?, 'purchased', CURRENT_TIMESTAMP)
        ''', (user_id, username, price))
        
        # Update user profile
        cursor.execute('''
            UPDATE user_profiles 
            SET total_gacha = total_gacha + 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error add_gacha_purchase: {e}")
        return False

# Initialize database
init_database()