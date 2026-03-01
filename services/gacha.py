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
import sqlite3
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
    "Premium_Name", "Vip_Username", "Short_Name", "Cool_User", "Best_Name",
    "Legend_User", "Pro_Account", "Elite_Name", "Master_User", "King_Username",
    "Queen_Name", "Star_User", "Gold_Account", "Silver_Name", "Bronze_User",
    "Alpha_User", "Beta_Test", "Gamma_Ray", "Delta_Force", "Omega_One",
    "Cyber_Punk", "Neon_User", "Pixel_Art", "Digital_One", "Virtual_User"
]

PRICE_RANGE = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 250, 300]

def generate_payment_link(payload, amount):
    """
    Generate link pembayaran Stars seperti di pay.py
    Format: https://t.me/$random_string
    """
    try:
        # Generate random string 24 bytes -> base64 URL safe
        random_bytes = os.urandom(24)
        link_id = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        
        # Format: https://t.me/$random_string
        payment_link = f"https://t.me/${link_id}"
        
        logger.info(f"Generated payment link: {payment_link}")
        return payment_link
    except Exception as e:
        logger.error(f"Error generating payment link: {e}")
        # Fallback ke format sederhana
        return f"https://t.me/{BOT_USERNAME}?start={payload}"

@gacha_bp.route('/')
def index():
    """Halaman utama gacha"""
    try:
        return render_template('gacha.html')
    except Exception as e:
        logger.error(f"Error rendering gacha page: {e}")
        return "Gacha page error", 500

@gacha_bp.route('/api/user/<int:user_id>')
def get_user(user_id):
    """Get user data by ID"""
    try:
        logger.info(f"Getting user data for ID: {user_id}")
        
        # Coba ambil user dari database
        user = users_db.get_user(user_id)
        logger.info(f"User from DB: {user}")
        
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
            logger.info(f"Gacha profile: {gacha_profile}")
        except Exception as e:
            logger.error(f"Error getting gacha profile: {e}")
            gacha_profile = {
                'user_id': user_id,
                'total_deposit': 0,
                'total_gacha': 0,
                'total_stars_spent': 0
            }
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user['user_id'],
                'username': user.get('username', ''),
                'full_name': user.get('full_name', ''),
                'balance': user.get('balance', 0),
                'total_deposit': gacha_profile.get('total_deposit', 0),
                'total_gacha': gacha_profile.get('total_gacha', 0)
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
            try:
                existing = gacha_db.get_pending_deposit(payload)
                if existing:
                    return jsonify({'success': False, 'message': 'Transaction already exists'}), 400
            except:
                pass
            
            return jsonify({'success': False, 'message': 'Failed to create transaction'}), 500
        
        logger.info(f"Transaction created with ID: {trans_id}")
        
        # Buat link pembayaran Stars seperti di pay.py
        # Format: https://t.me/$random_string
        payment_link = generate_payment_link(payload, amount)
        
        # Simpan mapping antara payment_link dan payload
        try:
            gacha_db.save_payment_link(payment_link, payload, trans_id)
            logger.info("Payment link saved successfully")
        except Exception as e:
            logger.error(f"Error saving payment link: {e}")
            # Lanjutkan walaupun error saving payment link
        
        # Hitung waktu expired (5 menit dari sekarang)
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()
        
        return jsonify({
            'success': True,
            'payload': payload,
            'payment_link': payment_link,
            'amount': amount,
            'transaction_id': trans_id,
            'expires_in': 300,  # 5 menit dalam detik
            'expires_at': expires_at,
            'user_id': user_id,
            'bot_username': BOT_USERNAME
        })
    except Exception as e:
        logger.error(f"Error in init_deposit: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

@gacha_bp.route('/api/deposit/check/<path:payload>')
def check_deposit(payload):
    """
    Cek status deposit berdasarkan payload
    """
    try:
        # Bersihkan payload jika ada karakter khusus
        payload = payload.strip()
        logger.info(f"Checking deposit status for payload: {payload}")
        
        # Cek transaksi pending
        trans = gacha_db.get_pending_deposit(payload)
        
        if trans:
            logger.info(f"Pending transaction found: {trans}")
            return jsonify({
                'success': True,
                'status': trans['status'],
                'amount': trans['amount'],
                'created_at': trans['created_at'],
                'completed_at': trans.get('completed_at')
            })
        
        # Cek apakah transaksi sudah completed
        try:
            conn = sqlite3.connect(config.GACHA_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM deposit_transactions 
                WHERE payload = ? AND status = 'completed'
            ''', (payload,))
            completed_trans = cursor.fetchone()
            conn.close()
            
            if completed_trans:
                logger.info(f"Completed transaction found: {dict(completed_trans)}")
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'amount': completed_trans['amount'],
                    'created_at': completed_trans['created_at'],
                    'completed_at': completed_trans['completed_at']
                })
        except Exception as e:
            logger.error(f"Error checking completed transaction: {e}")
        
        # Cek apakah transaksi expired
        try:
            conn = sqlite3.connect(config.GACHA_DB)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT status FROM deposit_transactions 
                WHERE payload = ?
            ''', (payload,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == 'expired':
                return jsonify({
                    'success': True,
                    'status': 'expired',
                    'message': 'Transaction expired'
                })
        except:
            pass
        
        return jsonify({'success': False, 'message': 'Transaction not found'}), 404
        
    except Exception as e:
        logger.error(f"Error in check_deposit: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

@gacha_bp.route('/api/deposit/verify', methods=['POST'])
def verify_deposit():
    """
    Verifikasi deposit dari bot (webhook)
    """
    try:
        data = request.json
        charge_id = data.get('charge_id')
        payload = data.get('payload')
        user_id = data.get('user_id')
        amount = data.get('amount')
        api_key = data.get('api_key')
        
        logger.info(f"Verify deposit request: charge_id={charge_id}, payload={payload}, user_id={user_id}, amount={amount}")
        
        # Verifikasi API key untuk keamanan
        expected_key = hashlib.sha256(config.SECRET_KEY.encode()).hexdigest()[:16]
        if api_key != expected_key:
            logger.warning(f"Unauthorized verify attempt with api_key: {api_key}")
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        if not all([charge_id, payload, user_id, amount]):
            missing = []
            if not charge_id: missing.append('charge_id')
            if not payload: missing.append('payload')
            if not user_id: missing.append('user_id')
            if not amount: missing.append('amount')
            return jsonify({'success': False, 'message': f'Missing parameters: {", ".join(missing)}'}), 400
        
        # Validasi tipe data
        try:
            user_id = int(user_id)
            amount = int(amount)
        except:
            return jsonify({'success': False, 'message': 'Invalid user_id or amount format'}), 400
        
        # Complete deposit transaction
        if gacha_db.complete_deposit_transaction(charge_id, payload):
            logger.info(f"Transaction completed in database: {payload}")
            
            # Update user balance
            success = users_db.update_balance(
                user_id, 
                amount, 
                'deposit', 
                f'Deposit via Stars: {charge_id}'
            )
            
            if success:
                logger.info(f"✅ Deposit verified and balance updated: User {user_id}, Amount {amount}, Charge {charge_id}")
            else:
                logger.warning(f"⚠️ Deposit verified but balance update failed: User {user_id}, Amount {amount}")
                
                # Coba update balance dengan method alternatif
                try:
                    # Update langsung via SQL jika perlu
                    conn = sqlite3.connect(config.USERS_DB)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE users SET balance = balance + ? WHERE user_id = ?
                    ''', (amount, user_id))
                    conn.commit()
                    conn.close()
                    logger.info(f"Balance updated via direct SQL: User {user_id}, Amount {amount}")
                    success = True
                except Exception as e:
                    logger.error(f"Failed to update balance via SQL: {e}")
            
            return jsonify({
                'success': True, 
                'message': 'Deposit verified successfully',
                'balance_updated': success
            })
        else:
            logger.warning(f"Failed to verify deposit in database: {payload}")
            
            # Cek apakah transaksi sudah ada tapi statusnya sudah completed
            try:
                conn = sqlite3.connect(config.GACHA_DB)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT status FROM deposit_transactions 
                    WHERE payload = ?
                ''', (payload,))
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] == 'completed':
                    logger.info(f"Transaction already completed: {payload}")
                    
                    # Update balance anyway
                    users_db.update_balance(user_id, amount, 'deposit', f'Deposit via Stars (reverify): {charge_id}')
                    
                    return jsonify({
                        'success': True,
                        'message': 'Transaction already completed',
                        'balance_updated': True
                    })
            except:
                pass
            
            return jsonify({'success': False, 'message': 'Failed to verify deposit'}), 400
            
    except Exception as e:
        logger.error(f"Error in verify_deposit: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

@gacha_bp.route('/api/deposit/cancel', methods=['POST'])
def cancel_deposit():
    """
    Batalkan deposit (jika user membatalkan)
    """
    try:
        data = request.json
        payload = data.get('payload')
        
        if not payload:
            return jsonify({'success': False, 'message': 'Missing payload'}), 400
        
        logger.info(f"Cancelling deposit: {payload}")
        
        # Expire transaction
        if gacha_db.expire_deposit_transaction(payload):
            return jsonify({'success': True, 'message': 'Deposit cancelled'})
        else:
            return jsonify({'success': False, 'message': 'Failed to cancel deposit'}), 400
            
    except Exception as e:
        logger.error(f"Error in cancel_deposit: {e}")
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

@gacha_bp.route('/api/gacha/random')
def get_random_username():
    """Get random username for gacha"""
    try:
        username = random.choice(USERNAME_POOL)
        price = random.choice(PRICE_RANGE)
        
        # Kadang tambahkan angka random
        if random.random() > 0.6:
            username = f"{username}{random.randint(1, 999)}"
        
        # Kadang tambahkan underscore
        if random.random() > 0.8:
            username = f"{username}_{random.randint(1, 99)}"
        
        # Kadang tambahkan huruf random di akhir
        if random.random() > 0.7:
            letters = 'abcdefghijklmnopqrstuvwxyz'
            username = f"{username}{random.choice(letters)}"
        
        logger.info(f"Generated random username: {username} with price: {price}")
        
        return jsonify({
            'success': True,
            'username': username,
            'price': price
        })
    except Exception as e:
        logger.error(f"Error in get_random_username: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@gacha_bp.route('/api/gacha/purchase', methods=['POST'])
def purchase_gacha():
    """Purchase gacha username"""
    try:
        data = request.json
        logger.info(f"Purchase gacha request: {data}")
        
        user_id = data.get('user_id')
        username = data.get('username')
        price = data.get('price')
        
        if not all([user_id, username, price]):
            return jsonify({'success': False, 'message': 'Missing parameters'}), 400
        
        # Validate price
        try:
            price = int(price)
        except:
            return jsonify({'success': False, 'message': 'Invalid price'}), 400
        
        # Validate username
        if not username or len(username) < 3:
            return jsonify({'success': False, 'message': 'Invalid username'}), 400
        
        # Get user
        user = users_db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Check balance
        if user['balance'] < price:
            return jsonify({'success': False, 'message': f'Insufficient balance. You have {user["balance"]} ⭐, need {price} ⭐'}), 400
        
        # Process purchase
        if users_db.update_balance(user_id, -price, 'gacha', f'Gacha purchase: {username}'):
            gacha_db.add_gacha_purchase(user_id, username, price)
            
            # Get updated balance
            updated_user = users_db.get_user(user_id)
            
            logger.info(f"Purchase successful: User {user_id}, Username {username}, Price {price}")
            
            return jsonify({
                'success': True,
                'message': 'Purchase successful',
                'username': username,
                'price': price,
                'new_balance': updated_user['balance']
            })
        else:
            logger.error(f"Purchase failed: Could not update balance for user {user_id}")
            return jsonify({'success': False, 'message': 'Purchase failed'}), 500
            
    except Exception as e:
        logger.error(f"Error in purchase_gacha: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Internal server error: {str(e)}'}), 500

@gacha_bp.route('/api/gacha/history/<int:user_id>')
def get_gacha_history(user_id):
    """Get user's gacha history"""
    try:
        logger.info(f"Getting gacha history for user: {user_id}")
        
        history = gacha_db.get_user_gacha_history(user_id)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error in get_gacha_history: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@gacha_bp.route('/api/gacha/history', methods=['DELETE'])
def clear_gacha_history():
    """Clear gacha history (admin only)"""
    try:
        data = request.json
        api_key = data.get('api_key') if data else None
        
        expected_key = hashlib.sha256(config.SECRET_KEY.encode()).hexdigest()[:16]
        if api_key != expected_key:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        # Implement clear history if needed
        # For now, just return success
        return jsonify({'success': True, 'message': 'History cleared'})
        
    except Exception as e:
        logger.error(f"Error in clear_gacha_history: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@gacha_bp.route('/api/stats')
def get_stats():
    """Get deposit statistics"""
    try:
        logger.info("Getting deposit statistics")
        
        stats = gacha_db.get_deposit_stats()
        
        # Get user stats
        users = users_db.get_all_users()
        total_users = len(users)
        total_balance = sum(u.get('balance', 0) for u in users)
        
        stats['total_users'] = total_users
        stats['total_balance'] = total_balance
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@gacha_bp.route('/api/balance/<int:user_id>')
def get_balance(user_id):
    """Get user balance"""
    try:
        user = users_db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'balance': user['balance']
        })
    except Exception as e:
        logger.error(f"Error in get_balance: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# Cron job endpoint untuk membersihkan transaksi expired
@gacha_bp.route('/api/cleanup', methods=['POST'])
def cleanup():
    """Cleanup expired transactions (panggil via cron)"""
    try:
        api_key = request.headers.get('X-API-Key')
        expected_key = hashlib.sha256(config.SECRET_KEY.encode()).hexdigest()[:16]
        
        if api_key != expected_key:
            logger.warning(f"Unauthorized cleanup attempt with API key: {api_key}")
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        logger.info("Running cleanup of expired transactions")
        
        cleaned = gacha_db.cleanup_expired_transactions()
        
        return jsonify({
            'success': True,
            'cleaned': cleaned,
            'message': f'Cleaned up {cleaned} expired transactions'
        })
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# Error handler untuk blueprint
@gacha_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@gacha_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500