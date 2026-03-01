import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv
import pytz
from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import parse_qs
import hmac
import hashlib

load_dotenv()

# Timezone Indonesia
WIB = pytz.timezone('Asia/Jakarta')

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///deposits.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    balance = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(WIB))
    
    transactions = relationship('Transaction', back_populates='user')

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Integer, nullable=False)
    payload = Column(String, unique=True)
    charge_id = Column(String, unique=True)
    status = Column(String, default='pending')  # pending, completed, refunded
    created_at = Column(DateTime, default=lambda: datetime.now(WIB))
    completed_at = Column(DateTime)
    
    user = relationship('User', back_populates='transactions')

# Create tables
Base.metadata.create_all(bind=engine)

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BOT_TOKEN = os.getenv('BOT_TOKEN')

def clean_json_string(json_str):
    """Hapus backslash escape yang gak perlu dari JSON string"""
    return json_str.replace('\\/', '/')

def verify_telegram_auth(auth_data):
    """Verifikasi data auth dari Telegram Login Widget"""
    if not auth_data:
        return None
    
    # Buat copy
    data = auth_data.copy()
    
    # Ambil hash
    check_hash = data.pop('hash', None)
    if not check_hash:
        print("No hash in auth data")
        return None
    
    # Parse user field jika ada
    if 'user' in data:
        try:
            # Parse user string menjadi object
            user_obj = json.loads(data['user'])
            # Stringify ulang tanpa spasi dan format standar
            data['user'] = json.dumps(user_obj, separators=(',', ':'))
        except Exception as e:
            print(f"Error parsing user: {e}")
            return None
    
    # Urutkan key secara alfabetis
    data_check_arr = []
    for key in sorted(data.keys()):
        value = data[key]
        data_check_arr.append(f"{key}={value}")
    
    data_check_string = "\n".join(data_check_arr)
    
    print(f"Data string for verification:\n{data_check_string}")
    
    # Buat secret key dari bot token (gunakan SHA256)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # Hitung hash menggunakan HMAC-SHA256
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Expected: {check_hash}")
    print(f"Got: {calculated_hash}")
    
    # Bandingkan hash (gunakan compare_digest untuk keamanan)
    if not hmac.compare_digest(calculated_hash, check_hash):
        return None
    
    # Parse user data untuk response
    if 'user' in data:
        try:
            data['user'] = json.loads(data['user'])
        except:
            pass
    
    return data

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Tambahkan route ini setelah CORS setup
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'message': 'Gacha API is running',
        'endpoints': ['/api/auth', '/api/user/<id>', '/api/create-deposit', '/api/check-transaction']
    })

@app.route('/api/test', methods=['GET'])
def test():
    """Endpoint test untuk cek koneksi"""
    return jsonify({'status': 'ok', 'message': 'API is working'})

@app.route('/api/auth', methods=['POST', 'OPTIONS'])
def auth():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    auth_data = request.json
    print(f"Received auth data: {auth_data}")
    
    # Verifikasi data
    verified_data = verify_telegram_auth(auth_data)
    if not verified_data:
        return jsonify({'error': 'Invalid authentication data'}), 401
    
    try:
        # Ambil user data dari verified_data
        user_data = verified_data.get('user', {})
        if isinstance(user_data, str):
            user_data = json.loads(user_data)
        
        telegram_id = user_data.get('id')
        if not telegram_id:
            return jsonify({'error': 'User ID not found'}), 400
            
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        username = user_data.get('username', '')
        
        print(f"✅ User authenticated: {telegram_id} - {username}")
        
    except Exception as e:
        print(f"Error parsing user data: {e}")
        return jsonify({'error': 'Invalid user data'}), 400
    
    # Simpan/update user ke database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                balance=0
            )
            db.add(user)
        else:
            # Update data user jika perlu
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
        
        db.commit()
        db.refresh(user)
        
        return jsonify({
            'id': user.telegram_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'balance': user.balance
        })
        
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        db.close()

@app.route('/api/user/<int:telegram_id>', methods=['GET'])
def get_user(telegram_id):
    """Get user data by Telegram ID"""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Ambil riwayat transaksi
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.status == 'completed'
    ).order_by(Transaction.completed_at.desc()).limit(10).all()
    
    trans_list = []
    for t in transactions:
        trans_list.append({
            'amount': t.amount,
            'charge_id': t.charge_id,
            'completed_at': t.completed_at.strftime('%d/%m/%Y %H:%M:%S') if t.completed_at else None
        })
    
    db.close()
    
    return jsonify({
        'id': user.telegram_id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'balance': user.balance,
        'transactions': trans_list
    })

@app.route('/api/create-deposit', methods=['POST'])
def create_deposit():
    """Buat deposit baru dan return payment link"""
    data = request.json
    telegram_id = data.get('telegram_id')
    amount = data.get('amount')
    
    if not telegram_id or not amount:
        return jsonify({'error': 'Missing parameters'}), 400
    
    try:
        amount = int(amount)
        if amount <= 0 or amount > 2500:
            return jsonify({'error': 'Invalid amount'}), 400
    except:
        return jsonify({'error': 'Invalid amount'}), 400
    
    db = SessionLocal()
    
    # Cari user
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Buat payload unik
    import random
    from datetime import datetime
    timestamp = int(datetime.now(WIB).timestamp())
    payload = f"deposit:{telegram_id}:{amount}:{random.randint(1000, 9999)}:{timestamp}"
    
    # Simpan transaksi
    transaction = Transaction(
        user_id=user.id,
        amount=amount,
        payload=payload,
        status='pending',
        created_at=datetime.now(WIB)
    )
    db.add(transaction)
    db.commit()
    db.close()
    
    # Panggil Bot API untuk createInvoiceLink
    import requests
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
    data = {
        "title": f"Deposit {amount} Stars",
        "description": f"Deposit {amount} Telegram Stars",
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": f"Deposit {amount} ⭐", "amount": amount}],
        "provider_token": ""
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get("ok"):
        return jsonify({
            'success': True,
            'payment_link': result['result'],
            'amount': amount
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('description', 'Unknown error')
        }), 500

@app.route('/api/check-transaction', methods=['POST'])
def check_transaction():
    """Cek status transaksi berdasarkan payload"""
    data = request.json
    payload = data.get('payload')
    
    if not payload:
        return jsonify({'error': 'Missing payload'}), 400
    
    db = SessionLocal()
    transaction = db.query(Transaction).filter(Transaction.payload == payload).first()
    
    if not transaction:
        db.close()
        return jsonify({'error': 'Transaction not found'}), 404
    
    result = {
        'status': transaction.status,
        'amount': transaction.amount
    }
    
    if transaction.status == 'completed':
        result['charge_id'] = transaction.charge_id
        result['completed_at'] = transaction.completed_at.strftime('%d/%m/%Y %H:%M:%S') if transaction.completed_at else None
    
    db.close()
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8008, debug=True)