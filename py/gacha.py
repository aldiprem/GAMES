import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for GitHub Pages

# Timezone Indonesia
WIB = pytz.timezone('Asia/Jakarta')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///gacha.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {})

# Buat SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Buat scoped session untuk Flask
db_session = scoped_session(SessionLocal)

Base = declarative_base()
Base.query = db_session.query_property()

# Models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    balance = Column(Integer, default=0)  # Stars balance
    created_at = Column(DateTime, default=lambda: datetime.now(WIB))
    updated_at = Column(DateTime, default=lambda: datetime.now(WIB), onupdate=lambda: datetime.now(WIB))
    
    # Relationships
    transactions = relationship('Transaction', back_populates='user', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'balance': self.balance,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Integer, nullable=False)  # Stars amount
    payload = Column(String(255), unique=True, nullable=False)
    charge_id = Column(String(255), unique=True)
    status = Column(String(50), default='pending')  # pending, completed, failed, refunded
    created_at = Column(DateTime, default=lambda: datetime.now(WIB))
    completed_at = Column(DateTime)
    refunded_at = Column(DateTime)
    
    # Relationships
    user = relationship('User', back_populates='transactions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'payload': self.payload,
            'charge_id': self.charge_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'refunded_at': self.refunded_at.isoformat() if self.refunded_at else None
        }

# Create tables
Base.metadata.create_all(bind=engine)

# Helper functions
def get_wib_time():
    return datetime.now(WIB)

def generate_payload(user_id, amount):
    """Generate unique payload for transaction"""
    import random
    timestamp = int(get_wib_time().timestamp())
    random_num = random.randint(1000, 9999)
    return f"deposit:{user_id}:{amount}:{random_num}:{timestamp}"

# API Routes
@app.before_request
def before_request():
    g.db = db_session

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'message': 'Gacha Stars API',
        'time': get_wib_time().isoformat()
    })

@app.route('/api/user', methods=['GET'])
def get_user():
    """Get or create user by Telegram ID"""
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'success': False, 'error': 'telegram_id required'}), 400
    
    try:
        telegram_id = int(telegram_id)
    except:
        return jsonify({'success': False, 'error': 'invalid telegram_id'}), 400
    
    # Get user data from request
    username = request.args.get('username', '')
    first_name = request.args.get('first_name', '')
    last_name = request.args.get('last_name', '')
    
    user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            balance=0
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@app.route('/api/user/balance', methods=['GET'])
def get_balance():
    """Get user balance"""
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'success': False, 'error': 'telegram_id required'}), 400
    
    try:
        telegram_id = int(telegram_id)
    except:
        return jsonify({'success': False, 'error': 'invalid telegram_id'}), 400
    
    user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return jsonify({'success': False, 'error': 'user not found'}), 404
    
    return jsonify({
        'success': True,
        'balance': user.balance
    })

@app.route('/api/deposit/create', methods=['POST'])
def create_deposit():
    """Create deposit invoice"""
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'no data provided'}), 400
    
    telegram_id = data.get('telegram_id')
    amount = data.get('amount')
    
    if not telegram_id or not amount:
        return jsonify({'success': False, 'error': 'telegram_id and amount required'}), 400
    
    try:
        telegram_id = int(telegram_id)
        amount = int(amount)
        
        if amount <= 0 or amount > 2500:
            return jsonify({'success': False, 'error': 'invalid amount (1-2500)'}), 400
            
    except:
        return jsonify({'success': False, 'error': 'invalid parameters'}), 400
    
    # Get or create user
    user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        # Get user details from request
        username = data.get('username', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            balance=0
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    # Generate unique payload
    payload = generate_payload(telegram_id, amount)
    
    # Create transaction record
    transaction = Transaction(
        user_id=user.id,
        amount=amount,
        payload=payload,
        status='pending'
    )
    db_session.add(transaction)
    db_session.commit()
    
    # Call Telegram Bot API to create invoice link
    bot_token = os.getenv('BOT_TOKEN')
    
    if not bot_token:
        return jsonify({'success': False, 'error': 'bot token not configured'}), 500
    
    url = f"https://api.telegram.org/bot{bot_token}/createInvoiceLink"
    
    invoice_data = {
        "title": f"Deposit {amount} Stars",
        "description": f"Deposit {amount} Telegram Stars",
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": f"Deposit {amount} ⭐", "amount": amount}],
        "provider_token": ""
    }
    
    try:
        import requests
        response = requests.post(url, json=invoice_data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            invoice_link = result['result']
            
            return jsonify({
                'success': True,
                'invoice_link': invoice_link,
                'payload': payload,
                'amount': amount,
                'transaction_id': transaction.id
            })
        else:
            # Delete pending transaction
            db_session.delete(transaction)
            db_session.commit()
            
            return jsonify({
                'success': False,
                'error': result.get('description', 'Failed to create invoice')
            }), 500
            
    except Exception as e:
        # Delete pending transaction
        db_session.delete(transaction)
        db_session.commit()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transactions/<telegram_id>', methods=['GET'])
def get_user_transactions(telegram_id):
    """Get user transactions"""
    try:
        telegram_id = int(telegram_id)
    except:
        return jsonify({'success': False, 'error': 'invalid telegram_id'}), 400
    
    user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return jsonify({'success': False, 'error': 'user not found'}), 404
    
    status = request.args.get('status', 'all')
    
    query = db_session.query(Transaction).filter(Transaction.user_id == user.id)
    
    if status != 'all':
        query = query.filter(Transaction.status == status)
    
    transactions = query.order_by(Transaction.created_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'transactions': [t.to_dict() for t in transactions]
    })

@app.route('/api/transaction/check/<payload>', methods=['GET'])
def check_transaction(payload):
    """Check transaction status by payload"""
    transaction = db_session.query(Transaction).filter(Transaction.payload == payload).first()
    
    if not transaction:
        return jsonify({'success': False, 'error': 'transaction not found'}), 404
    
    return jsonify({
        'success': True,
        'transaction': transaction.to_dict()
    })

@app.route('/api/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Webhook untuk menerima update dari Telegram (opsional)"""
    # Ini bisa digunakan jika ingin menerima update langsung
    # Tapi kita sudah menggunakan polling di b.py
    return jsonify({'status': 'ok'})

# ============ TAMBAHKAN ENDPOINT INI ============

@app.route('/api/test', methods=['GET'])
def api_test():
    """Endpoint untuk test koneksi"""
    return jsonify({
        'success': True,
        'status': 'online',
        'time': get_wib_time().isoformat()
    })

@app.route('/api/auth', methods=['POST'])
def api_auth():
    """Autentikasi user dari Telegram"""
    try:
        data = request.json
        if not data or 'user' not in data:
            return jsonify({'success': False, 'error': 'Invalid auth data'}), 400
        
        # Parse user data
        user_data = json.loads(data['user'])
        
        telegram_id = user_data.get('id')
        username = user_data.get('username', '')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        
        if not telegram_id:
            return jsonify({'success': False, 'error': 'No user ID'}), 400
        
        # Cari atau buat user
        user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                balance=0
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        
        return jsonify({
            'success': True,
            'id': user.telegram_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'balance': user.balance
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create-deposit', methods=['POST'])
def api_create_deposit():
    """Buat deposit invoice"""
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        amount = data.get('amount')
        
        if not telegram_id or not amount:
            return jsonify({'success': False, 'error': 'telegram_id and amount required'}), 400
        
        # Cari user
        user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Generate payload
        payload = generate_payload(telegram_id, amount)
        
        # Buat transaksi
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            payload=payload,
            status='pending'
        )
        db_session.add(transaction)
        db_session.commit()
        
        # Buat invoice link
        bot_token = os.getenv('BOT_TOKEN')
        url = f"https://api.telegram.org/bot{bot_token}/createInvoiceLink"
        
        invoice_data = {
            "title": f"Deposit {amount} Stars",
            "description": f"Deposit {amount} Telegram Stars",
            "payload": payload,
            "currency": "XTR",
            "prices": [{"label": f"Deposit {amount} ⭐", "amount": amount}],
            "provider_token": ""
        }
        
        response = requests.post(url, json=invoice_data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            return jsonify({
                'success': True,
                'payment_link': result['result'],
                'payload': payload,
                'amount': amount
            })
        else:
            # Hapus transaksi jika gagal
            db_session.delete(transaction)
            db_session.commit()
            return jsonify({'success': False, 'error': result.get('description', 'Failed to create invoice')}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-transaction', methods=['POST'])
def api_check_transaction():
    """Cek status transaksi"""
    try:
        data = request.json
        payload = data.get('payload')
        
        if not payload:
            return jsonify({'success': False, 'error': 'Payload required'}), 400
        
        transaction = db_session.query(Transaction).filter(Transaction.payload == payload).first()
        
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        return jsonify({
            'success': True,
            'status': transaction.status,
            'amount': transaction.amount,
            'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/<int:telegram_id>', methods=['GET'])
def api_user_detail(telegram_id):
    """Get user details and transactions"""
    try:
        user = db_session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Ambil transaksi
        transactions = db_session.query(Transaction).filter(
            Transaction.user_id == user.id
        ).order_by(Transaction.created_at.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'transactions': [t.to_dict() for t in transactions]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ AKHIR PENAMBAHAN ============

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# Ekspor untuk digunakan di b.py
__all__ = ['SessionLocal', 'User', 'Transaction', 'get_wib_time', 'engine', 'Base', 'db_session', 'app']