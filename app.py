from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import config
from services.users import users_bp
from services.stok import stok_bp
from services.bot import bot_bp
from services.gacha import gacha_bp
import os

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.secret_key = config.SECRET_KEY

# Update CORS untuk allow semua origin sementara (testing)
CORS(app, origins=['*'], allow_headers=['*'], methods=['GET', 'POST', 'PUT', 'DELETE'])

# Register blueprints
app.register_blueprint(users_bp)
app.register_blueprint(stok_bp)
app.register_blueprint(bot_bp)
app.register_blueprint(gacha_bp)

# Route untuk static files (fallback)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Middleware untuk cek auth (sederhana)
@app.before_request
def check_auth():
    # Skip untuk static files
    if request.path.startswith('/static'):
        return
    
    # Untuk API, cek header Authorization
    if request.path.startswith('/api'):
        user_id = request.headers.get('X-User-ID')
        if user_id and int(user_id) in config.ALLOWED_OWNER_IDS:
            return
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

# Route utama
@app.route('/')
def index():
    return render_template('panel.html')

@app.route('/gacha')
def gacha_page():
    return render_template('gacha.html')

# Route untuk cek status
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print(f"🚀 Panel running on http://{config.HOST}:{config.PORT}")
    print(f"📁 Static folder: {app.static_folder}")
    print(f"📁 Static URL: {app.static_url_path}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)