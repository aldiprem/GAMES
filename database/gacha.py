import sqlite3
import os
from datetime import datetime
import config
import traceback

DB_PATH = config.GACHA_DB

def init_database():
    """Inisialisasi database gacha"""
    try:
        # Pastikan direktori database ada
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabel deposit transactions (perbaiki struktur)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposit_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                charge_id TEXT,
                payload TEXT UNIQUE,
                payment_link TEXT,
                status TEXT DEFAULT 'pending',
                product_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        # Tabel payment_links untuk mapping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL,
                transaction_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        # Tabel gacha history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gacha_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                price INTEGER,
                status TEXT DEFAULT 'purchased',
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabel user profiles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                total_deposit INTEGER DEFAULT 0,
                total_gacha INTEGER DEFAULT 0,
                total_stars_spent INTEGER DEFAULT 0,
                last_deposit TIMESTAMP,
                last_gacha TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Buat indexes untuk performa
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deposit_user_id ON deposit_transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deposit_status ON deposit_transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deposit_payload ON deposit_transactions(payload)')
        
        conn.commit()
        conn.close()
        print(f"✅ Database gacha initialized at {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ Error initializing gacha database: {e}")
        traceback.print_exc()
        return False

def add_deposit_transaction(user_id, amount, payload, product_id='gacha_deposit'):
    """Tambah transaksi deposit baru"""
    try:
        print(f"📝 Adding deposit transaction: user_id={user_id}, amount={amount}, payload={payload}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Cek apakah payload sudah ada
        cursor.execute('SELECT id FROM deposit_transactions WHERE payload = ?', (payload,))
        existing = cursor.fetchone()
        if existing:
            print(f"⚠️ Payload already exists: {payload}")
            conn.close()
            return None
        
        # Insert transaksi
        cursor.execute('''
            INSERT INTO deposit_transactions 
            (user_id, amount, payload, product_id, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        ''', (user_id, amount, payload, product_id))
        
        trans_id = cursor.lastrowid
        print(f"✅ Transaction created with ID: {trans_id}")
        
        # Update atau insert user profile
        cursor.execute('''
            INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return trans_id
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Integrity Error in add_deposit_transaction: {e}")
        return None
    except Exception as e:
        print(f"❌ Error in add_deposit_transaction: {e}")
        traceback.print_exc()
        return None

def save_payment_link(payment_link, payload, transaction_id):
    """Simpan mapping payment link"""
    try:
        print(f"🔗 Saving payment link: {payment_link} for transaction {transaction_id}")
        
        # Extract link_id dari URL
        if payment_link.startswith('https://t.me/$'):
            link_id = payment_link.replace('https://t.me/$', '')
        else:
            link_id = payment_link
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Hapus link lama yang expired
        cursor.execute('''
            DELETE FROM payment_links 
            WHERE expires_at < datetime('now') OR status = 'expired'
        ''')
        
        # Insert link baru
        cursor.execute('''
            INSERT INTO payment_links (link_id, payload, transaction_id, status, expires_at)
            VALUES (?, ?, ?, 'active', datetime('now', '+5 minutes'))
        ''', (link_id, payload, transaction_id))
        
        # Update expires_at di deposit_transactions
        cursor.execute('''
            UPDATE deposit_transactions 
            SET expires_at = datetime('now', '+5 minutes')
            WHERE id = ?
        ''', (transaction_id,))
        
        conn.commit()
        conn.close()
        print(f"✅ Payment link saved successfully")
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Integrity Error in save_payment_link: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in save_payment_link: {e}")
        traceback.print_exc()
        return False

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
        
        if trans:
            return dict(trans)
        return None
        
    except Exception as e:
        print(f"Error get_pending_deposit: {e}")
        return None

def complete_deposit_transaction(charge_id, payload):
    """Selesaikan transaksi deposit"""
    try:
        print(f"💰 Completing deposit: charge_id={charge_id}, payload={payload}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Cek transaksi pending
        cursor.execute('''
            SELECT id, user_id, amount FROM deposit_transactions 
            WHERE payload = ? AND status = 'pending'
        ''', (payload,))
        trans = cursor.fetchone()
        
        if not trans:
            print(f"❌ Transaction not found or not pending: {payload}")
            conn.close()
            return False
        
        trans_id, user_id, amount = trans
        print(f"✅ Found transaction: ID={trans_id}, user={user_id}, amount={amount}")
        
        # Update transaksi
        cursor.execute('''
            UPDATE deposit_transactions 
            SET status = 'completed', charge_id = ?, completed_at = CURRENT_TIMESTAMP
            WHERE payload = ? AND status = 'pending'
        ''', (charge_id, payload))
        
        if cursor.rowcount == 0:
            print(f"❌ Failed to update transaction")
            conn.close()
            return False
        
        # Update payment link status
        cursor.execute('''
            UPDATE payment_links 
            SET status = 'used'
            WHERE payload = ? AND status = 'active'
        ''', (payload,))
        
        # Update user profile
        cursor.execute('''
            UPDATE user_profiles 
            SET total_deposit = total_deposit + ?, 
                total_stars_spent = total_stars_spent + ?,
                last_deposit = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (amount, amount, user_id))
        
        conn.commit()
        conn.close()
        print(f"✅ Transaction completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error complete_deposit_transaction: {e}")
        traceback.print_exc()
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
        
        # Ambil deposit terakhir (completed)
        cursor.execute('''
            SELECT * FROM deposit_transactions 
            WHERE user_id = ? AND status = 'completed'
            ORDER BY created_at DESC LIMIT 5
        ''', (user_id,))
        deposits = [dict(row) for row in cursor.fetchall()]
        
        # Ambil riwayat gacha
        cursor.execute('''
            SELECT * FROM gacha_history 
            WHERE user_id = ?
            ORDER BY purchased_at DESC LIMIT 10
        ''', (user_id,))
        gacha_history = [dict(row) for row in cursor.fetchall()]
        
        result = dict(profile) if profile else {
            'user_id': user_id,
            'total_deposit': 0,
            'total_gacha': 0,
            'total_stars_spent': 0
        }
        result['deposits'] = deposits
        result['gacha_history'] = gacha_history
        
        conn.close()
        return result
        
    except Exception as e:
        print(f"Error get_user_gacha_profile: {e}")
        traceback.print_exc()
        return {
            'user_id': user_id,
            'total_deposit': 0,
            'total_gacha': 0,
            'total_stars_spent': 0,
            'deposits': [],
            'gacha_history': []
        }

def add_gacha_purchase(user_id, username, price):
    """Catat pembelian gacha"""
    try:
        print(f"🎲 Adding gacha purchase: user={user_id}, username={username}, price={price}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert history
        cursor.execute('''
            INSERT INTO gacha_history (user_id, username, price, purchased_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, price))
        
        # Update user profile
        cursor.execute('''
            UPDATE user_profiles 
            SET total_gacha = total_gacha + 1, 
                last_gacha = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        print(f"✅ Gacha purchase recorded")
        return True
        
    except Exception as e:
        print(f"Error add_gacha_purchase: {e}")
        traceback.print_exc()
        return False

def cleanup_expired_transactions():
    """Bersihkan transaksi yang expired"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update status transaksi yang expired
        cursor.execute('''
            UPDATE deposit_transactions 
            SET status = 'expired'
            WHERE status = 'pending' AND datetime(created_at, '+5 minutes') < datetime('now')
        ''')
        expired_trans = cursor.rowcount
        
        # Update payment links yang expired
        cursor.execute('''
            UPDATE payment_links 
            SET status = 'expired'
            WHERE status = 'active' AND expires_at < datetime('now')
        ''')
        expired_links = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if expired_trans > 0 or expired_links > 0:
            print(f"🧹 Cleaned up {expired_trans} expired transactions and {expired_links} expired links")
        
        return expired_trans
        
    except Exception as e:
        print(f"Error cleanup_expired_transactions: {e}")
        return 0

# Initialize database
if __name__ != '__main__':
    init_database()