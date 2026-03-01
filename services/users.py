from flask import Blueprint, request, jsonify
from database import users as db_users

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('/', methods=['GET'])
def get_all_users():
    users = db_users.get_all_users()
    return jsonify({'success': True, 'data': users})

@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = db_users.get_user(user_id)
    if user:
        return jsonify({'success': True, 'data': user})
    return jsonify({'success': False, 'message': 'User not found'}), 404

@users_bp.route('/<int:user_id>/balance', methods=['PUT'])
def update_user_balance(user_id):
    data = request.json
    amount = data.get('amount', 0)
    action = data.get('action')
    description = data.get('description', 'Manual adjustment')
    
    user = db_users.get_user(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if action == 'reset':
        success = db_users.reset_balance(user_id)
        if success:
            db_users.update_balance(user_id, 0, 'withdraw', 'Reset balance')
    elif action == 'add':
        success = db_users.update_balance(user_id, amount, 'deposit', description)
    elif action == 'subtract':
        success = db_users.update_balance(user_id, -amount, 'withdraw', description)
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    if success:
        updated_user = db_users.get_user(user_id)
        return jsonify({'success': True, 'data': updated_user})
    
    return jsonify({'success': False, 'message': 'Failed to update balance'}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = db_users.get_user(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if db_users.delete_user(user_id):
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    
    return jsonify({'success': False, 'message': 'Failed to delete user'}), 500

@users_bp.route('/<int:user_id>/transactions', methods=['GET'])
def get_user_transactions(user_id):
    limit = request.args.get('limit', 50, type=int)
    transactions = db_users.get_transactions(user_id, limit)
    return jsonify({'success': True, 'data': transactions})

@users_bp.route('/transactions', methods=['GET'])
def get_all_transactions():
    limit = request.args.get('limit', 100, type=int)
    transactions = db_users.get_transactions(None, limit)
    return jsonify({'success': True, 'data': transactions})