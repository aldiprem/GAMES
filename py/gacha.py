import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv
import pytz
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS, cross_origin
from urllib.parse import parse_qs
import hmac
import hashlib
import json
import logging
import requests
import random

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

# Timezone Indonesia
WIB = pytz.timezone('Asia/Jakarta')

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///deposits.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {})
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

# CORS Configuration - Yang paling penting!
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Untuk development, di production ganti dengan domain specific
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Middleware untuk handle CORS preflight
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

BOT_TOKEN = os.getenv('BOT_TOKEN')

def verify_telegram_auth(auth_data):
    """Verifikasi data auth dari Telegram Login Widget"""
    if not auth_data:
        return None
    
    # Buat copy
    data = auth_data.copy()
    
    # Ambil hash
    check_hash = data.pop('hash', None)
    if not check_hash:
        logger.error("No hash in auth data")
        return None
    
    # Parse user field jika ada
    if 'user' in data:
        try:
            # Parse user string menjadi object
            if isinstance(data['user'], str):
                user_obj = json.loads(data['user'])
                # Stringify ulang tanpa spasi dan format standar
                data['user'] = json.dumps(user_obj, separators=(',', ':'))
        except Exception as e:
            logger.error(f"Error parsing user: {e}")
            return None
    
    # Urutkan key secara alfabetis
    data_check_arr = []
    for key in sorted(data.keys()):
        value = data[key]
        data_check_arr.append(f"{key}={value}")
    
    data_check_string = "\n".join(data_check_arr)
    
    logger.debug(f"Data string for verification:\n{data_check_string}")
    
    # Buat secret key dari bot token (gunakan SHA256)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # Hitung hash menggunakan HMAC-SHA256
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    logger.debug(f"Expected: {check_hash}")
    logger.debug(f"Got: {calculated_hash}")
    
    # Bandingkan hash (gunakan compare_digest untuk keamanan)
    if not hmac.compare_digest(calculated_hash, check_hash):
        logger.error(f"Hash mismatch! Expected: {check_hash}, Got: {calculated_hash}")
        return None
    
    # Parse user data untuk response
    if 'user' in data:
        try:
            if isinstance(data['user'], str):
                data['user'] = json.loads(data['user'])
        except:
            pass
    
    return data

@app.route('/', methods=['GET'])
@cross_origin()
def home():
    return jsonify({
        'status': 'online',
        'message': 'Gacha API is running',
        'endpoints': ['/api/auth', '/api/user/<id>', '/api/create-deposit', '/api/check-transaction']
    })

@app.route('/api/test', methods=['GET'])
@cross_origin()
def test():
    """Endpoint test untuk cek koneksi"""
    return jsonify({'status': 'ok', 'message': 'API is working', 'timestamp': datetime.now().isoformat()})

@app.route('/api/auth', methods=['POST', 'OPTIONS'])
@cross_origin()
def auth():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        auth_data = request.json
        logger.info(f"Received auth data: {auth_data}")
        
        if not auth_data:
            return jsonify({'error': 'No data received'}), 400
        
        # Verifikasi data
        verified_data = verify_telegram_auth(auth_data)
        if not verified_data:
            return jsonify({'error': 'Invalid authentication data'}), 401
        
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
        
        logger.info(f"✅ User authenticated: {telegram_id} - {username}")
        
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
            
            response_data = {
                'id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'balance': user.balance
            }
            
            logger.info(f"User data sent: {response_data}")
            return jsonify(response_data)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            return jsonify({'error': 'Database error'}), 500
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<int:telegram_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_user(telegram_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    """Get user data by Telegram ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
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
        
        return jsonify({
            'id': user.telegram_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'balance': user.balance,
            'transactions': trans_list
        })
    finally:
        db.close()

@app.route('/api/create-deposit', methods=['POST', 'OPTIONS'])
@cross_origin()
def create_deposit():
    if request.method == 'OPTIONS':
        return '', 200
        
    """Buat deposit baru dan return payment link"""
    try:
        data = request.json
        logger.info(f"Create deposit request: {data}")
        
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        
        if not telegram_id or not amount:
            return jsonify({'error': 'Missing parameters'}), 400
        
        try:
            amount = int(amount)
            if amount <= 0 or amount > 2500:
                return jsonify({'error': 'Invalid amount (must be 1-2500)'}), 400
        except:
            return jsonify({'error': 'Invalid amount format'}), 400
        
        db = SessionLocal()
        
        try:
            # Cari user
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Buat payload unik
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
            
            # Panggil Bot API untuk createInvoiceLink
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
            invoice_data = {
                "title": f"Deposit {amount} Stars",
                "description": f"Deposit {amount} Telegram Stars",
                "payload": payload,
                "currency": "XTR",
                "prices": [{"label": f"Deposit {amount} ⭐", "amount": amount}],
                "provider_token": ""
            }
            
            logger.info(f"Calling Telegram API: {url}")
            response = requests.post(url, json=invoice_data, timeout=10)
            result = response.json()
            
            logger.info(f"Telegram API response: {result}")
            
            if result.get("ok"):
                return jsonify({
                    'success': True,
                    'payment_link': result['result'],
                    'amount': amount,
                    'payload': payload
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('description', 'Unknown error from Telegram')
                }), 500
                
        finally:
            db.close()
            
    except requests.exceptions.Timeout:
        logger.error("Telegram API timeout")
        return jsonify({'error': 'Telegram API timeout'}), 504
    except requests.exceptions.ConnectionError:
        logger.error("Telegram API connection error")
        return jsonify({'error': 'Cannot connect to Telegram API'}), 502
    except Exception as e:
        logger.error(f"Create deposit error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-transaction', methods=['POST', 'OPTIONS'])
@cross_origin()
def check_transaction():
    if request.method == 'OPTIONS':
        return '', 200
        
    """Cek status transaksi berdasarkan payload"""
    try:
        data = request.json
        payload = data.get('payload')
        
        if not payload:
            return jsonify({'error': 'Missing payload'}), 400
        
        db = SessionLocal()
        try:
            transaction = db.query(Transaction).filter(Transaction.payload == payload).first()
            
            if not transaction:
                return jsonify({'error': 'Transaction not found'}), 404
            
            result = {
                'status': transaction.status,
                'amount': transaction.amount
            }
            
            if transaction.status == 'completed':
                result['charge_id'] = transaction.charge_id
                result['completed_at'] = transaction.completed_at.strftime('%d/%m/%Y %H:%M:%S') if transaction.completed_at else None
            
            logger.info(f"Transaction check: {payload} -> {result}")
            return jsonify(result)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Check transaction error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask server on http://0.0.0.0:8008")
    app.run(host='0.0.0.0', port=8008, debug=True, threaded=True)