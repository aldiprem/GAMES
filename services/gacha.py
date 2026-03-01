from flask import Blueprint, render_template, request, jsonify
from database import users as users_db
from database import gacha as gacha_db
import config
import random
import time
import base64
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gacha_bp = Blueprint('gacha', __name__, url_prefix='/gacha')

USERNAME_POOL = [
    "Stok_Habis", "Coming_Soon", "Username1", "Gacha_Bot", "Telegram_User",
    "Premium_Name", "Vip_Username", "Short_Name", "Cool_User", "Best_Name"
]

PRICE_RANGE = [1, 5, 10, 20, 30, 50, 100, 150, 200]

BOT_USERNAME = config.BOT_USERNAME
WEBSITE_URL = config.WEBSITE_URL

def generate_stars_payment_link(payload, amount):
    return f"https://t.me/{BOT_USERNAME}?start={payload}"

@gacha_bp.route('/')
def index():
    return render_template('gacha.html')

@gacha_bp.route('/api/user/<int:user_id>')
def get_user(user_id):
    try:
        user = users_db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        gacha_profile = gacha_db.get_user_gacha_profile(user_id)
        
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
        return jsonify({'success': False, 'message': 'Internal server error'})

@gacha_bp.route('/api/deposit/init', methods=['POST'])
def init_deposit():
    try:
        data = request.json
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not user_id or not amount:
            return jsonify({'success': False, 'message': 'Missing parameters'})
        
        try:
            amount = int(amount)
            if amount < 1:
                return jsonify({'success': False, 'message': 'Amount must be at least 1'})
            if amount > 2500:
                return jsonify({'success': False, 'message': 'Maximum deposit is 2500 Stars'})
        except:
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        timestamp = int(time.time())
        random_code = random.randint(1000, 9999)
        payload = f"deposit:{user_id}:{amount}:{timestamp}:{random_code}"
        
        trans_id = gacha_db.add_deposit_transaction(user_id, amount, payload)
        
        if not trans_id:
            return jsonify({'success': False, 'message': 'Failed to create transaction'})
        
        payment_link = generate_stars_payment_link(payload, amount)
        
        return jsonify({
            'success': True,
            'payload': payload,
            'payment_link': payment_link,
            'amount': amount,
            'transaction_id': trans_id,
            'expires_in': 300,
            'user_id': user_id,
            'bot_username': BOT_USERNAME
        })
    except Exception as e:
        logger.error(f"Error in init_deposit: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@gacha_bp.route('/api/deposit/check/<path:payload>')
def check_deposit(payload):
    try:
        trans = gacha_db.get_pending_deposit(payload)
        
        if not trans:
            return jsonify({'success': False, 'message': 'Transaction not found'})
        
        return jsonify({
            'success': True,
            'status': trans['status'],
            'amount': trans['amount'],
            'created_at': trans['created_at'],
            'completed_at': trans.get('completed_at')
        })
    except Exception as e:
        logger.error(f"Error in check_deposit: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@gacha_bp.route('/api/deposit/verify', methods=['POST'])
def verify_deposit():
    try:
        data = request.json
        charge_id = data.get('charge_id')
        payload = data.get('payload')
        user_id = data.get('user_id')
        amount = data.get('amount')
        api_key = data.get('api_key')
        
        if api_key != hashlib.sha256(config.SECRET_KEY.encode()).hexdigest()[:16]:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        if not all([charge_id, payload, user_id, amount]):
            return jsonify({'success': False, 'message': 'Missing parameters'})
        
        if gacha_db.complete_deposit_transaction(charge_id, payload):
            users_db.update_balance(user_id, amount, 'deposit', f'Deposit via Stars: {charge_id}')
            logger.info(f"✅ Deposit verified: User {user_id}, Amount {amount}, Charge {charge_id}")
            return jsonify({'success': True, 'message': 'Deposit verified successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to verify deposit'})
    except Exception as e:
        logger.error(f"Error in verify_deposit: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@gacha_bp.route('/api/gacha/random')
def get_random_username():
    try:
        username = random.choice(USERNAME_POOL)
        price = random.choice(PRICE_RANGE)
        
        if random.random() > 0.5:
            username = f"{username}{random.randint(1, 999)}"
        
        return jsonify({
            'success': True,
            'username': username,
            'price': price
        })
    except Exception as e:
        logger.error(f"Error in get_random_username: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@gacha_bp.route('/api/gacha/purchase', methods=['POST'])
def purchase_gacha():
    try:
        data = request.json
        user_id = data.get('user_id')
        username = data.get('username')
        price = data.get('price')
        
        if not all([user_id, username, price]):
            return jsonify({'success': False, 'message': 'Missing parameters'})
        
        user = users_db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        if user['balance'] < price:
            return jsonify({'success': False, 'message': 'Insufficient balance'})
        
        if users_db.update_balance(user_id, -price, 'gacha', f'Gacha purchase: {username}'):
            gacha_db.add_gacha_purchase(user_id, username, price)
            return jsonify({
                'success': True,
                'message': 'Purchase successful',
                'username': username,
                'price': price,
                'new_balance': user['balance'] - price
            })
        else:
            return jsonify({'success': False, 'message': 'Purchase failed'})
    except Exception as e:
        logger.error(f"Error in purchase_gacha: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})