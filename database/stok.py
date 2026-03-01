import sqlite3
import os
import re
from datetime import datetime
import config

DB_PATH = config.STOK_DB

def init_database():
    """Inisialisasi database stok username"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabel stok username
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stok_username (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            clean_username TEXT NOT NULL,
            status TEXT DEFAULT 'available' CHECK(status IN ('available', 'claimed', 'reserved')),
            claimed_by INTEGER,
            claimed_at TIMESTAMP,
            price INTEGER DEFAULT 0,
            category TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_claimed_by ON stok_username(claimed_by)')
    
    # Insert default categories
    default_categories = [
        ('premium', 'Username premium 5-6 karakter'),
        ('standard', 'Username standar 7-12 karakter'),
        ('vip', 'Username VIP 3-4 karakter'),
        ('random', 'Username random generator')
    ]
    
    for name, desc in default_categories:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, description)
                VALUES (?, ?)
            ''', (name, desc))
        except:
            pass
    
    conn.commit()
    conn.close()

def clean_username(username):
    """
    Bersihkan username dari @ dan spasi
    Contoh: @username123 -> username123
    """
    if not username:
        return ''
    # Hapus @ di awal, spasi, dan ubah ke lowercase
    clean = username.lower().strip().replace('@', '')
    # Hapus karakter khusus kecuali underscore
    clean = re.sub(r'[^a-z0-9_]', '', clean)
    return clean

def add_usernames(usernames_text):
    """
    Tambah satu atau banyak username (pisahkan dengan koma atau newline)
    Format: @user1, @user2, user3 atau per baris
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Split dengan koma atau newline
    if ',' in usernames_text:
        raw_usernames = [u.strip() for u in usernames_text.split(',')]
    else:
        raw_usernames = [u.strip() for u in usernames_text.split('\n') if u.strip()]
    
    added = []
    failed = []
    skipped = []
    
    for raw_username in raw_usernames:
        if not raw_username:
            continue
        
        # Bersihkan username
        clean = clean_username(raw_username)
        
        # Validasi panjang username
        if len(clean) < 3:
            skipped.append(f"{raw_username} (terlalu pendek, min 3 karakter)")
            continue
        if len(clean) > 32:
            skipped.append(f"{raw_username} (terlalu panjang, max 32 karakter)")
            continue
        
        # Format username dengan @
        username_with_at = f"@{clean}"
        
        try:
            cursor.execute('''
                INSERT INTO stok_username (username, clean_username, status)
                VALUES (?, ?, 'available')
            ''', (username_with_at, clean))
            added.append(username_with_at)
        except sqlite3.IntegrityError:
            failed.append(username_with_at)
        except Exception as e:
            skipped.append(f"{raw_username} ({str(e)})")
    
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'added': added,
        'failed': failed,
        'skipped': skipped,
        'total_added': len(added),
        'total_failed': len(failed),
        'total_skipped': len(skipped)
    }

def get_all_stok(filters=None):
    """
    Ambil semua stok username dengan filter opsional
    filters: {'status': 'available', 'category': 'premium', 'limit': 100}
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM stok_username WHERE 1=1"
    params = []
    
    if filters:
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
        
        if filters.get('category'):
            query += " AND category = ?"
            params.append(filters['category'])
        
        if filters.get('search'):
            query += " AND (username LIKE ? OR clean_username LIKE ?)"
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])
    
    query += " ORDER BY CASE status " \
             "WHEN 'available' THEN 1 " \
             "WHEN 'reserved' THEN 2 " \
             "WHEN 'claimed' THEN 3 END, created_at DESC"
    
    if filters and filters.get('limit'):
        query += " LIMIT ?"
        params.append(filters['limit'])
    
    cursor.execute(query, params)
    stok = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stok

def get_available_stok(limit=100):
    """Ambil stok yang available saja"""
    return get_all_stok({'status': 'available', 'limit': limit})

def get_claimed_stok(user_id=None, limit=100):
    """Ambil stok yang sudah di-claim"""
    filters = {'status': 'claimed', 'limit': limit}
    if user_id:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM stok_username 
            WHERE status = 'claimed' AND claimed_by = ?
            ORDER BY claimed_at DESC LIMIT ?
        ''', (user_id, limit))
        stok = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return stok
    return get_all_stok(filters)

def search_usernames(query):
    """
    Cari username dengan fuzzy search:
    - Menghilangkan satu huruf untuk mencari kemiripan
    - Support partial matching
    """
    if not query or len(query) < 2:
        return []
    
    clean_query = clean_username(query)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Cari exact match dulu
    cursor.execute('''
        SELECT * FROM stok_username 
        WHERE clean_username = ? OR username = ?
        ORDER BY 
            CASE status 
                WHEN 'available' THEN 1
                WHEN 'reserved' THEN 2
                WHEN 'claimed' THEN 3
            END
    ''', (clean_query, f"@{clean_query}"))
    
    exact_matches = [dict(row) for row in cursor.fetchall()]
    
    # Cari partial match (username mengandung query)
    cursor.execute('''
        SELECT * FROM stok_username 
        WHERE (clean_username LIKE ? OR username LIKE ?)
        AND clean_username != ?
        AND username != ?
        ORDER BY 
            CASE status 
                WHEN 'available' THEN 1
                WHEN 'reserved' THEN 2
                WHEN 'claimed' THEN 3
            END,
            LENGTH(clean_username) ASC
        LIMIT 50
    ''', (f'%{clean_query}%', f'%{clean_query}%', clean_query, f"@{clean_query}"))
    
    partial_matches = [dict(row) for row in cursor.fetchall()]
    
    # Generate variasi dengan menghilangkan satu huruf (untuk typo)
    variations = []
    if len(clean_query) >= 4:
        for i in range(len(clean_query)):
            var = clean_query[:i] + clean_query[i+1:]
            if len(var) >= 3:
                variations.append(var)
    
    fuzzy_matches = []
    if variations:
        placeholders = ','.join(['?'] * len(variations))
        cursor.execute(f'''
            SELECT * FROM stok_username 
            WHERE clean_username IN ({placeholders})
            AND clean_username NOT LIKE ?
            AND clean_username NOT IN (?, ?)
            ORDER BY 
                CASE status 
                    WHEN 'available' THEN 1
                    WHEN 'reserved' THEN 2
                    WHEN 'claimed' THEN 3
                END
            LIMIT 30
        ''', variations + [f'%{clean_query}%', clean_query, f"@{clean_query}"])
        fuzzy_matches = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Gabungkan hasil tanpa duplikasi
    seen_ids = set()
    results = []
    
    for item in exact_matches:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            results.append(item)
    
    for item in partial_matches:
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

def get_stok_by_username(username):
    """Ambil stok berdasarkan username"""
    clean = clean_username(username)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stok_username WHERE clean_username = ?", (clean,))
    stok = cursor.fetchone()
    conn.close()
    return dict(stok) if stok else None

def update_stok(stok_id, data):
    """Update data stok"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    allowed_fields = ['status', 'price', 'category', 'tags']
    
    for key, value in data.items():
        if key in allowed_fields:
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
    """
    Claim username (ubah status jadi claimed)
    Returns: (success, message, data)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Cek apakah username masih available
        cursor.execute('''
            SELECT * FROM stok_username 
            WHERE id = ? AND status = 'available'
        ''', (stok_id,))
        stok = cursor.fetchone()
        
        if not stok:
            conn.close()
            return False, "Username tidak tersedia atau sudah di-claim", None
        
        # Update status
        cursor.execute('''
            UPDATE stok_username 
            SET status = 'claimed', claimed_by = ?, claimed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'available'
        ''', (user_id, stok_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            
            # Ambil data yang sudah diupdate
            cursor.execute('''
                SELECT * FROM stok_username WHERE id = ?
            ''', (stok_id,))
            updated = cursor.fetchone()
            
            # Konversi ke dict
            columns = [description[0] for description in cursor.description]
            updated_dict = dict(zip(columns, updated))
            
            conn.close()
            return True, "Username berhasil di-claim", updated_dict
        else:
            conn.close()
            return False, "Gagal meng-claim username", None
            
    except Exception as e:
        print(f"Error claim username: {e}")
        conn.close()
        return False, f"Error: {str(e)}", None

def reserve_username(stok_id, user_id, duration_minutes=30):
    """
    Reserve username untuk sementara (status reserved)
    Biasanya digunakan saat proses checkout
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE stok_username 
            SET status = 'reserved', claimed_by = ?, claimed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'available'
        ''', (user_id, stok_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error reserve username: {e}")
        return False
    finally:
        conn.close()

def release_reserved(duration_minutes=30):
    """
    Release username yang di-reserve lebih dari durasi tertentu
    (Cron job untuk membersihkan reserve yang expired)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE stok_username 
            SET status = 'available', claimed_by = NULL, claimed_at = NULL
            WHERE status = 'reserved' 
            AND datetime(claimed_at, '+' || ? || ' minutes') < datetime('now')
        ''', (duration_minutes,))
        released = cursor.rowcount
        conn.commit()
        return released
    except Exception as e:
        print(f"Error release reserved: {e}")
        return 0
    finally:
        conn.close()

def get_user_claimed(user_id):
    """Ambil semua username yang pernah di-claim oleh user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM stok_username 
        WHERE claimed_by = ?
        ORDER BY claimed_at DESC
    ''', (user_id,))
    claimed = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return claimed

def get_categories():
    """Ambil semua kategori"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY name")
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return categories

def add_category(name, description=''):
    """Tambah kategori baru"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO categories (name, description)
            VALUES (?, ?)
        ''', (name.lower(), description))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error add category: {e}")
        return None
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
    
    # Statistik per kategori
    cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM stok_username 
        WHERE category IS NOT NULL 
        GROUP BY category
    ''')
    by_category = dict(cursor.fetchall())
    
    # Statistik per user (top claimers)
    cursor.execute('''
        SELECT claimed_by, COUNT(*) as count 
        FROM stok_username 
        WHERE claimed_by IS NOT NULL 
        GROUP BY claimed_by 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    top_claimers = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'total': total,
        'available': available,
        'claimed': claimed,
        'reserved': reserved,
        'by_category': by_category,
        'top_claimers': top_claimers
    }

def bulk_delete(ids):
    """Hapus multiple stok berdasarkan list ID"""
    if not ids:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        placeholders = ','.join(['?'] * len(ids))
        cursor.execute(f"DELETE FROM stok_username WHERE id IN ({placeholders})", ids)
        deleted = cursor.rowcount
        conn.commit()
        return deleted
    except Exception as e:
        print(f"Error bulk delete: {e}")
        return 0
    finally:
        conn.close()

def import_from_text(text):
    """
    Import username dari text (satu username per baris)
    Format: @username atau username saja
    """
    lines = text.strip().split('\n')
    usernames = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):  # Abaikan komentar
            usernames.append(line)
    
    if not usernames:
        return {
            'success': False,
            'message': 'Tidak ada username valid ditemukan',
            'added': [],
            'failed': []
        }
    
    return add_usernames(','.join(usernames))

def export_to_csv():
    """Export semua stok ke format CSV"""
    import csv
    import io
    
    stok = get_all_stok()
    output = io.StringIO()
    
    if stok:
        fieldnames = ['id', 'username', 'clean_username', 'status', 'claimed_by', 
                     'claimed_at', 'price', 'category', 'tags', 'created_at']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(stok)
    
    return output.getvalue()

# Initialize database
init_database()