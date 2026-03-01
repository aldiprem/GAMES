import sqlite3
import os
from datetime import datetime
import config

DB_PATH = config.USERS_DB

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            balance INTEGER DEFAULT 0,
            total_gacha INTEGER DEFAULT 0,
            total_claim INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            last_active TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT CHECK(type IN ('deposit', 'withdraw', 'gacha', 'claim')),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (7998861975,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, full_name, balance, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (7998861975, 'owner', 'Bot Owner', 1000000, 1))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def add_user(user_id, username=None, full_name=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, full_name, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, full_name))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error add user: {e}")
        return False
    finally:
        conn.close()

def update_balance(user_id, amount, transaction_type, description=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (amount, user_id))
        
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, transaction_type, description))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error update balance: {e}")
        return False
    finally:
        conn.close()

def reset_balance(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error reset balance: {e}")
        return False
    finally:
        conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error delete user: {e}")
        return False
    finally:
        conn.close()

def get_transactions(user_id=None, limit=50):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
    else:
        cursor.execute('''
            SELECT * FROM transactions 
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
    
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transactions

# Initialize database
init_database()