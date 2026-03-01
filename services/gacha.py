from flask import Blueprint, render_template, request, jsonify
from database import users as users_db
from database import gacha as gacha_db
import config
import random
import time
import logging
import hashlib
import base64
import os
import traceback
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gacha_bp = Blueprint('gacha', __name__, url_prefix='/gacha')

# Konfigurasi
BOT_USERNAME = config.BOT_USERNAME
WEBSITE_URL = config.WEBSITE_URL

# Pool username untuk gacha
USERNAME_POOL = [
    "Stok_Habis", "Coming_Soon", "Username1", "Gacha_Bot", "Telegram_User",
    "Premium_Name", "Vip_Username", "Short_Name", "Cool_User", "Best_Name"
]

PRICE_RANGE = [1, 5, 10, 20, 30, 50, 100, 150, 200]

def generate_payment_link(payload, amount):
    """
    Generate link pembayaran Stars seperti di pay.py
    Format: https://t.me/$random_string
    """
    # Generate random string 24 bytes -> base64 URL safe
    random_bytes = os.urandom(24)
    link_id = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    
    # Format: https://t.me/$random_string
    return f"https://t.me/${link_id}"

@gacha_bp.route('/')
def index():
    """Halaman utama gacha"""
    return render_template('gacha.html')

@gacha_bp.route('/api/user/<int:user_id>')
def get_user(user_id):
    """Get user data by ID"""
    try:
        logger.info(f"Getting user data for ID: {user_id}")
        
        # Coba ambil user dari database
        user = users_db.get_user(user_id)
        
        if not user:
            # Jika user tidak ada, buat user baru
            logger.info(f"User {user_id} not found, creating new user")
            users_db.add_user(user_id, f"user_{user_id}", f"User {user_id}")
            user = users_db.get_user(user_id)
            
            if not user:
                return jsonify({'success': False, 'message': 'Failed to create user'}), 500
        
        # Ambil profile gacha
        try:
            gacha_profile = gacha_db.get_user_gacha_profile(user_id)
        except Exception as e:
            logger.error(f"Error getting gacha profile: {e}")
            gacha_profile = None
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user['user_id'],
                'username': user.get('username', ''),
                'full_name': user.get('full_name', ''),
                'balance': user.get('balance', 0),
                'total_deposit': gacha_profile.get('total_deposit', 0) if gacha_profile else 0,
                'total_gacha': gacha_profile.get('total_gacha', 0) if gacha_profile else 0
            }
        })
    except Exception as e:
        logger.error(f"Error in get_user: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

@gacha_bp.route('/api/deposit/init', methods=['POST'])
def init_deposit():
    """
    Inisialisasi deposit Stars
    Format payload: deposit:{user_id}:{amount}:{timestamp}:{random}
    """
    try:
        data = request.json
        logger.info(f"Init deposit request: {data}")
        
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not user_id or not amount:
            return jsonify({'success': False, 'message': 'Missing parameters'}), 400
        
        try:
            amount = int(amount)
            if amount < 1:
                return jsonify({'success': False, 'message': 'Amount must be at least 1'}), 400
            if amount > 2500:
                return jsonify({'success': False, 'message': 'Maximum deposit is 2500 Stars'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        # Generate payload unik
        timestamp = int(time.time())
        random_code = random.randint(1000, 9999)
        payload = f"deposit:{user_id}:{amount}:{timestamp}:{random_code}"
        
        logger.info(f"Generated payload: {payload}")
        
        # Simpan transaksi di database
        trans_id = gacha_db.add_deposit_transaction(user_id, amount, payload)
        
        if not trans_id:
            logger.error("Failed to create transaction in database")
            
            # Cek apakah payload sudah ada
            existing = gacha_db.get_pending_deposit(payload)
            if existing:
                return jsonify({'success': False, 'message': 'Transaction already exists'}), 400
            
            return jsonify({'success': False, 'message': 'Failed to create transaction'}), 500
        
        logger.info(f"Transaction created with ID: {trans_id}")
        
        # Buat link pembayaran Stars
        payment_link = generate_payment_link(payload, amount)
        logger.info(f"Generated payment link: {payment_link}")
        
        # Simpan mapping antara payment_link dan payload
        link_saved = gacha_db.save_payment_link(payment_link, payload, trans_id)
        if not link_saved:
            logger.warning("Failed to save payment link, but transaction was created")
        
        # Hitung waktu expired (5 menit dari sekarang)
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
        
        return jsonify({
            'success': True,
            'payload': payload,
            'payment_link': payment_link,
            'amount': amount,
            'transaction_id': trans_id,
            'expires_in': 300,
            'expires_at': expires_at,
            'user_id': user_id,
            'bot_username': BOT_USERNAME
        })
        
    except Exception as e:
        logger.error(f"Error in init_deposit: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

# ... rest of the functions remain the same ...