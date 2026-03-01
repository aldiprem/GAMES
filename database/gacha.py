import sqlite3
import os
from datetime import datetime
import config

DB_PATH = config.GACHA_DB

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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

def add_deposit_transaction(user_id, amount, payload, product_id='gacha_deposit'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO deposit_transactions (user_id, amount, payload, product_id, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (user_id, amount, payload, product_id))
        
        cursor.execute('''
            INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)
        ''', (user_id,))
        
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error add deposit: {e}")
        return None
    finally:
        conn.close()

def complete_deposit_transaction(charge_id, payload):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT user_id, amount FROM deposit_transactions 
            WHERE payload = ? AND status = 'pending'
        ''', (payload,))
        trans = cursor.fetchone()
        
        if not trans:
            return False
        
        user_id, amount = trans
        
        cursor.execute('''
            UPDATE deposit_transactions 
            SET status = 'completed', charge_id = ?, completed_at = CURRENT_TIMESTAMP
            WHERE payload = ?
        ''', (charge_id, payload))
        
        cursor.execute('''
            UPDATE user_profiles 
            SET total_deposit = total_deposit + ?, last_deposit = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (amount, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error complete deposit: {e}")
        return False
    finally:
        conn.close()

def get_user_gacha_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM user_profiles WHERE user_id = ?
        ''', (user_id,))
        profile = cursor.fetchone()
        
        cursor.execute('''
            SELECT * FROM deposit_transactions 
            WHERE user_id = ? AND status = 'completed'
            ORDER BY created_at DESC LIMIT 10
        ''', (user_id,))
        deposits = [dict(row) for row in cursor.fetchall()]
        
        result = dict(profile) if profile else {
            'user_id': user_id,
            'total_deposit': 0,
            'total_gacha': 0
        }
        result['deposits'] = deposits
        
        return result
    except Exception as e:
        print(f"Error get profile: {e}")
        return None
    finally:
        conn.close()

def get_pending_deposit(payload):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM deposit_transactions 
            WHERE payload = ? AND status = 'pending'
        ''', (payload,))
        trans = cursor.fetchone()
        return dict(trans) if trans else None
    except Exception as e:
        print(f"Error get pending: {e}")
        return None
    finally:
        conn.close()

def add_gacha_purchase(user_id, username, price):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO gacha_history (user_id, username, price, status, purchased_at)
            VALUES (?, ?, ?, 'purchased', CURRENT_TIMESTAMP)
        ''', (user_id, username, price))
        
        cursor.execute('''
            UPDATE user_profiles 
            SET total_gacha = total_gacha + 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error add gacha: {e}")
        return False
    finally:
        conn.close()

# Initialize database
init_database()