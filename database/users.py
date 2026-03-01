import sqlite3
import os
from datetime import datetime
import config

DB_PATH = config.USERS_DB

def init_database():
    """Inisialisasi database users"""
    try:
        # Pastikan direktori database ada
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buat tabel users
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
        
        # Buat tabel transactions
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
        
        # Cek apakah owner sudah ada
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (7998861975,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, balance, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', (7998861975, 'owner', 'Bot Owner', 1000000, 1))
        
        conn.commit()
        conn.close()
        print(f"✅ Database users initialized at {DB_PATH}")
    except Exception as e:
        print(f"❌ Error initializing users database: {e}")

def get_user(user_id):
    """Ambil user berdasarkan user_id"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error get_user: {e}")
        return None

def get_all_users():
    """Ambil semua users"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        print(f"Error get_all_users: {e}")
        return []

def add_user(user_id, username=None, full_name=None):
    """Tambah user baru"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Cek apakah user sudah ada
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            # Update last_active jika user sudah ada
            cursor.execute('''
                UPDATE users 
                SET last_active = CURRENT_TIMESTAMP,
                    username = COALESCE(?, username),
                    full_name = COALESCE(?, full_name)
                WHERE user_id = ?
            ''', (username, full_name, user_id))
        else:
            # Insert user baru
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, full_name))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error add_user: {e}")
        return False

def update_balance(user_id, amount, transaction_type, description=""):
    """Update saldo user dan catat transaksi"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (amount, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return False
        
        # Catat transaksi
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, transaction_type, description))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error update_balance: {e}")
        return False

def reset_balance(user_id):
    """Reset saldo user ke 0"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        print(f"Error reset_balance: {e}")
        return False

def delete_user(user_id):
    """Hapus user dan semua transaksinya"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Hapus transaksi dulu
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        
        # Hapus user
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        print(f"Error delete_user: {e}")
        return False

def get_transactions(user_id=None, limit=50):
    """Ambil riwayat transaksi"""
    try:
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
    except Exception as e:
        print(f"Error get_transactions: {e}")
        return []

# Initialize database
init_database()