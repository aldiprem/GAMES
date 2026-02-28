import sqlite3
import os
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'stok.db')

def init_database():
    """Inisialisasi database stok username"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabel stok username
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stok_username (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            clean_username TEXT NOT NULL,  -- Username tanpa @
            status TEXT DEFAULT 'available' CHECK(status IN ('available', 'claimed', 'reserved')),
            claimed_by INTEGER,
            claimed_at TIMESTAMP,
            price INTEGER DEFAULT 0,
            category TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (claimed_by) REFERENCES users(user_id)
        )
    ''')
    
    # Tabel kategori
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Index untuk pencarian cepat
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clean_username ON stok_username(clean_username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON stok_username(status)')
    
    conn.commit()
    conn.close()

def clean_username(username):
    """Bersihkan username dari @ dan spasi"""
    return username.lower().strip().replace('@', '')

def add_usernames(usernames_text):
    """Tambah satu atau banyak username (pisahkan dengan koma)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Split username dengan koma
    raw_usernames = [u.strip() for u in usernames_text.split(',')]
    
    added = []
    failed = []
    
    for raw_username in raw_usernames:
        if not raw_username:
            continue
            
        clean = clean_username(raw_username)
        username_with_at = f"@{clean}" if not clean.startswith('@') else clean
        
        try:
            cursor.execute('''
                INSERT INTO stok_username (username, clean_username)
                VALUES (?, ?)
            ''', (username_with_at, clean))
            added.append(username_with_at)
        except sqlite3.IntegrityError:
            failed.append(username_with_at)
    
    conn.commit()
    conn.close()
    
    return {
        'added': added,
        'failed': failed,
        'total_added': len(added),
        'total_failed': len(failed)
    }

def get_all_stok():
    """Ambil semua stok username"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM stok_username 
        ORDER BY 
            CASE status 
                WHEN 'available' THEN 1
                WHEN 'reserved' THEN 2
                WHEN 'claimed' THEN 3
            END,
            created_at DESC
    ''')
    stok = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stok

def search_usernames(query):
    """
    Cari username dengan fuzzy search:
    - Menghilangkan satu huruf untuk mencari kemiripan
    """
    if not query:
        return get_all_stok()
    
    clean_query = clean_username(query)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Cari exact match dulu
    cursor.execute('''
        SELECT * FROM stok_username 
        WHERE clean_username LIKE ? OR username LIKE ?
        ORDER BY 
            CASE status 
                WHEN 'available' THEN 1
                WHEN 'reserved' THEN 2
                WHEN 'claimed' THEN 3
            END
    ''', (f'%{clean_query}%', f'%{clean_query}%'))
    
    exact_matches = [dict(row) for row in cursor.fetchall()]
    
    # Generate variasi dengan menghilangkan satu huruf
    variations = []
    for i in range(len(clean_query)):
        # Hapus huruf ke-i
        var = clean_query[:i] + clean_query[i+1:]
        if len(var) >= 3:  # Minimal 3 huruf
            variations.append(var)
    
    fuzzy_matches = []
    if variations:
        placeholders = ','.join(['?'] * len(variations))
        cursor.execute(f'''
            SELECT * FROM stok_username 
            WHERE clean_username IN ({placeholders})
            AND clean_username NOT LIKE ?
            ORDER BY 
                CASE status 
                    WHEN 'available' THEN 1
                    WHEN 'reserved' THEN 2
                    WHEN 'claimed' THEN 3
                END
        ''', variations + [f'%{clean_query}%'])
        fuzzy_matches = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Gabungkan hasil (exact dulu, baru fuzzy)
    seen_ids = set()
    results = []
    
    for item in exact_matches:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            results.append(item)
    
    for item in fuzzy_matches:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            results.append(item)
    
    return results

def get_stok_by_id(stok_id):
    """Ambil stok berdasarkan ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stok_username WHERE id = ?", (stok_id,))
    stok = cursor.fetchone()
    conn.close()
    return dict(stok) if stok else None

def update_stok(stok_id, data):
    """Update data stok"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    for key, value in data.items():
        if key in ['status', 'price', 'category', 'tags']:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return False
    
    values.append(stok_id)
    
    try:
        cursor.execute(f'''
            UPDATE stok_username 
            SET {', '.join(updates)}
            WHERE id = ?
        ''', values)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error update stok: {e}")
        return False
    finally:
        conn.close()

def delete_stok(stok_id):
    """Hapus stok berdasarkan ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stok_username WHERE id = ?", (stok_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error delete stok: {e}")
        return False
    finally:
        conn.close()

def claim_username(stok_id, user_id):
    """Claim username (ubah status jadi claimed)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE stok_username 
            SET status = 'claimed', claimed_by = ?, claimed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'available'
        ''', (user_id, stok_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error claim username: {e}")
        return False
    finally:
        conn.close()

def get_stats():
    """Ambil statistik stok"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM stok_username")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM stok_username WHERE status = 'available'")
    available = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM stok_username WHERE status = 'claimed'")
    claimed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM stok_username WHERE status = 'reserved'")
    reserved = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'available': available,
        'claimed': claimed,
        'reserved': reserved
    }

# Initialize database
init_database()
