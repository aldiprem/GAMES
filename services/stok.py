from flask import Blueprint, request, jsonify
from database import stok as db_stok

stok_bp = Blueprint('stok', __name__, url_prefix='/api/stok')

@stok_bp.route('/', methods=['GET'])
def get_stok():
    limit = request.args.get('limit', 100, type=int)
    usernames = db_stok.get_available_usernames(limit)
    return jsonify({'success': True, 'data': usernames})

@stok_bp.route('/', methods=['POST'])
def add_usernames():
    data = request.json
    usernames = data.get('usernames')
    
    if not usernames:
        return jsonify({'success': False, 'message': 'Usernames required'}), 400
    
    if db_stok.add_usernames(usernames):
        return jsonify({'success': True, 'message': 'Usernames added successfully'})
    
    return jsonify({'success': False, 'message': 'Failed to add usernames'}), 500

@stok_bp.route('/random', methods=['GET'])
def get_random():
    username = db_stok.get_random_username()
    if username:
        return jsonify({'success': True, 'data': username})
    return jsonify({'success': False, 'message': 'No usernames available'}), 404