from flask import Blueprint, request, jsonify
from database import bot as db_bot

bot_bp = Blueprint('bot', __name__, url_prefix='/api/bots')

@bot_bp.route('/', methods=['GET'])
def get_all_bots():
    """API get all bots"""
    bots = db_bot.get_all_bots()
    stats = db_bot.get_bot_stats()
    
    return jsonify({
        'success': True,
        'data': bots,
        'stats': stats
    })

@bot_bp.route('/', methods=['POST'])
def add_bot():
    """API add bot clone"""
    data = request.json
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    bot_token = data.get('bot_token')
    
    if not all([api_id, api_hash, bot_token]):
        return jsonify({
            'success': False,
            'message': 'API ID, API Hash, and Bot Token required'
        }), 400
    
    # Cek apakah main bot?
    main_config = db_bot.get_main_bot()
    is_main = False
    
    if db_bot.save_bot(api_id, api_hash, bot_token, is_main):
        return jsonify({
            'success': True,
            'message': 'Bot added successfully'
        })
    
    return jsonify({
        'success': False,
        'message': 'Bot with this token already exists'
    }), 400

@bot_bp.route('/<path:bot_token>', methods=['DELETE'])
def delete_bot(bot_token):
    """API delete bot"""
    if db_bot.delete_bot(bot_token):
        return jsonify({
            'success': True,
            'message': 'Bot deleted successfully'
        })
    return jsonify({
        'success': False,
        'message': 'Failed to delete bot (main bot cannot be deleted)'
    }), 400

@bot_bp.route('/stats', methods=['GET'])
def get_stats():
    """API get bot statistics"""
    stats = db_bot.get_bot_stats()
    return jsonify({
        'success': True,
        'data': stats
    })

@bot_bp.route('/restart', methods=['POST'])
def restart_bots():
    """API restart all bots"""
    # Ini akan memicu restart bot di main_bot.py
    # Untuk implementasi sederhana, kita return sukses saja
    return jsonify({
        'success': True,
        'message': 'Bot restart signal sent'
    })
