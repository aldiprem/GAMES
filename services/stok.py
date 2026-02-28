from flask import Blueprint, request, jsonify
from database import stok as db_stok

stok_bp = Blueprint('stok', __name__, url_prefix='/api/stok')

@stok_bp.route('/', methods=['GET'])
def get_all_stok():
    """API get all stok"""
    search = request.args.get('search', '')
    
    if search:
        data = db_stok.search_usernames(search)
    else:
        data = db_stok.get_all_stok()
    
    return jsonify({
        'success': True,
        'data': data,
        'total': len(data)
    })

@stok_bp.route('/', methods=['POST'])
def add_stok():
    """API add stok username"""
    data = request.json
    usernames = data.get('usernames', '')
    
    if not usernames:
        return jsonify({
            'success': False,
            'message': 'Usernames required'
        }), 400
    
    result = db_stok.add_usernames(usernames)
    
    return jsonify({
        'success': True,
        'message': f'Added {result["total_added"]} usernames',
        'data': result
    })

@stok_bp.route('/<int:stok_id>', methods=['GET'])
def get_stok(stok_id):
    """API get stok by ID"""
    stok = db_stok.get_stok_by_id(stok_id)
    if stok:
        return jsonify({
            'success': True,
            'data': stok
        })
    return jsonify({
        'success': False,
        'message': 'Stok not found'
    }), 404

@stok_bp.route('/<int:stok_id>', methods=['PUT'])
def update_stok(stok_id):
    """API update stok"""
    data = request.json
    
    # Filter data yang boleh diupdate
    update_data = {}
    for key in ['status', 'price', 'category', 'tags']:
        if key in data:
            update_data[key] = data[key]
    
    if not update_data:
        return jsonify({
            'success': False,
            'message': 'No valid fields to update'
        }), 400
    
    if db_stok.update_stok(stok_id, update_data):
        updated = db_stok.get_stok_by_id(stok_id)
        return jsonify({
            'success': True,
            'message': 'Stok updated successfully',
            'data': updated
        })
    
    return jsonify({
        'success': False,
        'message': 'Failed to update stok'
    }), 500

@stok_bp.route('/<int:stok_id>', methods=['DELETE'])
def delete_stok(stok_id):
    """API delete stok"""
    if db_stok.delete_stok(stok_id):
        return jsonify({
            'success': True,
            'message': 'Stok deleted successfully'
        })
    return jsonify({
        'success': False,
        'message': 'Failed to delete stok'
    }), 500

@stok_bp.route('/stats', methods=['GET'])
def get_stats():
    """API get stok statistics"""
    stats = db_stok.get_stats()
    return jsonify({
        'success': True,
        'data': stats
    })

@stok_bp.route('/search', methods=['GET'])
def search_stok():
    """API search usernames"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({
            'success': False,
            'message': 'Query required'
        }), 400
    
    results = db_stok.search_usernames(query)
    return jsonify({
        'success': True,
        'data': results,
        'total': len(results)
    })
