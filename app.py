from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import time
import random
import requests
import json
from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, GiftEvent, LikeEvent, FollowEvent, ShareEvent
import asyncio

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'tiktok-snake-battle-secret'
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25, async_mode='threading')

# Game state
game_state = {
    'male_score': 0,
    'female_score': 0,
    'round': 1,
    'game_active': True,
    'snake': {
        'body': [(7, 4), (6, 4), (5, 4), (4, 4)],
        'direction': 'RIGHT',
    },
    'apples': [],
    'bombs': [],
    'grid_size': {'width': 15, 'height': 10},
    'last_update': time.time()
}

# TikTok configuration
tiktok_config = {
    'connected': False,
    'test_mode': True,  # Default test mode ON
    'username': 'indoclipmedia',
    'client': None,
    'thread': None
}

# Gift mapping untuk TikTok
GIFT_MAPPING = {
    'Rose': {'team': 'female', 'type': 'apple', 'points': 5},
    'Mawar': {'team': 'female', 'type': 'apple', 'points': 5},
    'Bouquet': {'team': 'female', 'type': 'apple', 'points': 10},
    'TikTok': {'team': 'male', 'type': 'apple', 'points': 5},
    'Diamond': {'team': 'male', 'type': 'apple', 'points': 10},
    
    # Bomb gifts
    'Jari Hati': {'team': 'both', 'type': 'bomb', 'points': 1},
    'Nasi Padang': {'team': 'both', 'type': 'bomb', 'points': 1},
    'Love Bang': {'team': 'both', 'type': 'bomb', 'points': 1},
}

def spawn_apple():
    """Spawn random apple on grid"""
    attempts = 0
    max_attempts = 100
    
    while attempts < max_attempts:
        x = random.randint(0, game_state['grid_size']['width'] - 1)
        y = random.randint(0, game_state['grid_size']['height'] - 1)
        
        # Check if position is free
        position_free = True
        
        # Check snake body
        for segment in game_state['snake']['body']:
            if segment[0] == x and segment[1] == y:
                position_free = False
                break
        
        # Check apples
        for apple in game_state['apples']:
            if apple['x'] == x and apple['y'] == y:
                position_free = False
                break
        
        # Check bombs
        for bomb in game_state['bombs']:
            if bomb['x'] == x and bomb['y'] == y:
                position_free = False
                break
        
        if position_free:
            game_state['apples'].append({'x': x, 'y': y, 'value': 1})
            return True
        
        attempts += 1
    
    return False

def spawn_bomb():
    """Spawn random bomb on grid"""
    attempts = 0
    max_attempts = 100
    
    while attempts < max_attempts:
        x = random.randint(0, game_state['grid_size']['width'] - 1)
        y = random.randint(0, game_state['grid_size']['height'] - 1)
        
        # Check if position is free
        position_free = True
        
        # Check snake body
        for segment in game_state['snake']['body']:
            if segment[0] == x and segment[1] == y:
                position_free = False
                break
        
        # Check apples
        for apple in game_state['apples']:
            if apple['x'] == x and apple['y'] == y:
                position_free = False
                break
        
        # Check bombs
        for bomb in game_state['bombs']:
            if bomb['x'] == x and bomb['y'] == y:
                position_free = False
                break
        
        if position_free:
            game_state['bombs'].append({'x': x, 'y': y})
            return True
        
        attempts += 1
    
    return False

def spawn_multiple_apples(count, team=None):
    """Spawn multiple apples at once"""
    spawned = 0
    for _ in range(min(count, 15)):  # Limit to 15 apples max
        if spawn_apple():
            if team and len(game_state['apples']) > 0:
                game_state['apples'][-1]['team'] = team
            spawned += 1
    return spawned

def spawn_mixed_items(like_count):
    """Spawn random mix of apples and bombs based on likes"""
    total_items = min(like_count // 1000, 25)  # 1 item per 1000 likes, max 25
    if total_items == 0:
        return 0, 0
    
    # Random distribution between apples and bombs
    apples = random.randint(0, total_items)
    bombs = total_items - apples
    
    # Spawn apples
    apple_count = 0
    for _ in range(apples):
        if spawn_apple():
            apple_count += 1
    
    # Spawn bombs
    bomb_count = 0
    for _ in range(bombs):
        if spawn_bomb():
            bomb_count += 1
    
    return apple_count, bomb_count

def move_snake():
    """Move snake in zigzag pattern"""
    if not game_state['game_active']:
        return
    
    head = game_state['snake']['body'][0]
    direction = game_state['snake']['direction']
    
    # Calculate new head position
    if direction == 'RIGHT':
        new_head = (head[0] + 1, head[1])
    else:  # LEFT
        new_head = (head[0] - 1, head[1])
    
    # Zigzag pattern: when hitting walls
    if new_head[0] >= game_state['grid_size']['width']:  # Hit right wall (male side)
        new_head = (game_state['grid_size']['width'] - 1, head[1] + 1)
        if new_head[1] >= game_state['grid_size']['height']:
            new_head = (game_state['grid_size']['width'] - 1, 0)
        game_state['snake']['direction'] = 'LEFT'
        print(f"Hit right wall, going left at y={new_head[1]}")
    
    elif new_head[0] < 0:  # Hit left wall (female side)
        new_head = (0, head[1] + 1)
        if new_head[1] >= game_state['grid_size']['height']:
            new_head = (0, 0)
        game_state['snake']['direction'] = 'RIGHT'
        print(f"Hit left wall, going right at y={new_head[1]}")
    
    # Check top/bottom boundaries
    if new_head[1] < 0:
        new_head = (new_head[0], 0)
    elif new_head[1] >= game_state['grid_size']['height']:
        new_head = (new_head[0], game_state['grid_size']['height'] - 1)
    
    # Check apple collision
    apple_eaten = None
    apple_index = -1
    for i, apple in enumerate(game_state['apples']):
        if apple['x'] == new_head[0] and apple['y'] == new_head[1]:
            apple_eaten = apple
            apple_index = i
            break
    
    # Check bomb collision
    bomb_eaten = None
    bomb_index = -1
    for i, bomb in enumerate(game_state['bombs']):
        if bomb['x'] == new_head[0] and bomb['y'] == new_head[1]:
            bomb_eaten = bomb
            bomb_index = i
            break
    
    # Update snake
    if apple_eaten:
        # Grow snake (don't remove tail)
        game_state['snake']['body'].insert(0, new_head)
        # Remove eaten apple
        if apple_index >= 0:
            game_state['apples'].pop(apple_index)
        
        # Add score based on which side the apple was on
        if new_head[0] < game_state['grid_size']['width'] // 2:
            game_state['female_score'] += 10
        else:
            game_state['male_score'] += 10
        
        # Spawn new apple
        spawn_apple()
        print(f"Apple eaten! New scores: M={game_state['male_score']}, F={game_state['female_score']}")
        
    elif bomb_eaten:
        # Shrink snake (remove tail) if possible
        if len(game_state['snake']['body']) > 2:
            game_state['snake']['body'].pop()  # Remove tail
        game_state['snake']['body'].insert(0, new_head)
        
        # Remove eaten bomb
        if bomb_index >= 0:
            game_state['bombs'].pop(bomb_index)
        
        # Reduce score
        if new_head[0] < game_state['grid_size']['width'] // 2:
            game_state['female_score'] = max(0, game_state['female_score'] - 5)
        else:
            game_state['male_score'] = max(0, game_state['male_score'] - 5)
        
        print(f"Bomb eaten! New scores: M={game_state['male_score']}, F={game_state['female_score']}")
        
    else:
        # Normal move
        game_state['snake']['body'].insert(0, new_head)
        game_state['snake']['body'].pop()
    
    # Check self collision (game over)
    head_pos = game_state['snake']['body'][0]
    for segment in game_state['snake']['body'][1:]:
        if head_pos[0] == segment[0] and head_pos[1] == segment[1]:
            game_state['game_active'] = False
            winner = 'female' if game_state['male_score'] < game_state['female_score'] else 'male'
            socketio.emit('game_over', {'winner': winner})
            print(f"Game Over! Winner: {winner}")
            break

def game_loop():
    """Main game loop"""
    last_move = time.time()
    move_interval = 0.2  # Move every 0.2 seconds (5 cells per second)
    update_counter = 0
    
    while True:
        current_time = time.time()
        
        if game_state['game_active'] and current_time - last_move >= move_interval:
            move_snake()
            # Emit update to all clients
            socketio.emit('game_update', game_state)
            last_move = current_time
            update_counter += 1
        
        # Spawn random apple if none exist (maintain 3-5 apples)
        if len(game_state['apples']) < 3 and game_state['game_active']:
            if spawn_apple():
                socketio.emit('game_update', game_state)
        
        # Occasionally spawn random apples
        if game_state['game_active'] and random.random() < 0.02:  # 2% chance each loop
            if len(game_state['apples']) < 8:  # Max 8 apples
                if spawn_apple():
                    socketio.emit('game_update', game_state)
        
        time.sleep(0.05)

# TikTok Live Client Handlers
async def tiktok_on_comment(event: CommentEvent):
    """Handle TikTok comments"""
    print(f"Comment from {event.user.unique_id}: {event.comment}")
    socketio.emit('tiktok_event', {
        'type': 'comment',
        'user': event.user.unique_id,
        'message': event.comment
    })

async def tiktok_on_gift(event: GiftEvent):
    """Handle TikTok gifts"""
    gift_name = event.gift.name
    gift_count = event.gift.count
    gift_repeat = event.gift.repeat_count if hasattr(event.gift, 'repeat_count') else 1
    
    print(f"Gift from {event.user.unique_id}: {gift_name} x{gift_count} (repeat: {gift_repeat})")
    
    # Map gift to game action
    gift_info = None
    for key, value in GIFT_MAPPING.items():
        if key.lower() in gift_name.lower():
            gift_info = value
            break
    
    if gift_info:
        total_points = gift_count * gift_info.get('points', 1)
        
        if gift_info['type'] == 'apple':
            if gift_info['team'] == 'female':
                count = spawn_multiple_apples(total_points, 'female')
                socketio.emit('gift_received', {
                    'team': 'female',
                    'gift': gift_name,
                    'value': total_points,
                    'apples': count,
                    'user': event.user.unique_id
                })
            elif gift_info['team'] == 'male':
                count = spawn_multiple_apples(total_points, 'male')
                socketio.emit('gift_received', {
                    'team': 'male',
                    'gift': gift_name,
                    'value': total_points,
                    'apples': count,
                    'user': event.user.unique_id
                })
        elif gift_info['type'] == 'bomb':
            for _ in range(total_points):
                if spawn_bomb():
                    socketio.emit('gift_received', {
                        'team': 'both',
                        'gift': gift_name,
                        'value': 1,
                        'bomb': 1,
                        'user': event.user.unique_id
                    })
    
    # Emit game update
    socketio.emit('game_update', game_state)

async def tiktok_on_like(event: LikeEvent):
    """Handle TikTok likes"""
    like_count = event.likeCount if hasattr(event, 'likeCount') else event.count
    print(f"Likes from {event.user.unique_id}: {like_count}")
    
    # Convert likes to game items (1000 likes = random items)
    if like_count >= 1000:
        apples, bombs = spawn_mixed_items(like_count)
        socketio.emit('gift_received', {
            'team': 'both',
            'gift': '❤️ Like',
            'value': like_count // 1000,
            'apples': apples,
            'bombs': bombs,
            'user': event.user.unique_id
        })
        socketio.emit('game_update', game_state)

async def tiktok_on_follow(event: FollowEvent):
    """Handle TikTok follows"""
    print(f"New follower: {event.user.unique_id}")
    socketio.emit('tiktok_event', {
        'type': 'follow',
        'user': event.user.unique_id
    })

async def tiktok_on_share(event: ShareEvent):
    """Handle TikTok shares"""
    print(f"Share from: {event.user.unique_id}")
    # Share bisa spawn apple random
    if spawn_apple():
        socketio.emit('gift_received', {
            'team': 'both',
            'gift': '🔄 Share',
            'value': 1,
            'apples': 1,
            'user': event.user.unique_id
        })
        socketio.emit('game_update', game_state)

def start_tiktok_client():
    """Start TikTok Live client in a separate thread"""
    if not tiktok_config['username'] or tiktok_config['username'] == 'YOUR_TIKTOK_USERNAME':
        print("⚠️ TikTok username not configured. Using test mode only.")
        return
    
    async def run_client():
        try:
            client = TikTokLiveClient(unique_id=f"@{tiktok_config['username']}")
            
            # Add event handlers
            client.on("comment")(tiktok_on_comment)
            client.on("gift")(tiktok_on_gift)
            client.on("like")(tiktok_on_like)
            client.on("follow")(tiktok_on_follow)
            client.on("share")(tiktok_on_share)
            
            tiktok_config['client'] = client
            tiktok_config['connected'] = True
            
            print(f"🟢 Connecting to TikTok Live @{tiktok_config['username']}...")
            await client.start()
        except Exception as e:
            print(f"🔴 TikTok connection error: {e}")
            tiktok_config['connected'] = False
            tiktok_config['client'] = None
    
    # Run client in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_client())

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('game_update', game_state)
    emit('tiktok_status', {'connected': tiktok_config['connected']})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('reset_game')
def handle_reset():
    game_state['male_score'] = 0
    game_state['female_score'] = 0
    game_state['round'] = 1
    game_state['game_active'] = True
    game_state['snake'] = {
        'body': [(7, 4), (6, 4), (5, 4), (4, 4)],
        'direction': 'RIGHT',
    }
    game_state['apples'] = []
    game_state['bombs'] = []
    
    # Spawn initial apples
    for _ in range(3):
        spawn_apple()
    
    emit('game_update', game_state)
    print('Game reset')

@socketio.on('toggle_tiktok_test')
def handle_toggle_test():
    """Toggle TikTok test mode"""
    tiktok_config['test_mode'] = not tiktok_config['test_mode']
    tiktok_config['connected'] = tiktok_config['test_mode']  # For UI, always show connected in test mode
    emit('tiktok_status', {'connected': tiktok_config['connected']})
    print(f"Test mode: {'ON' if tiktok_config['test_mode'] else 'OFF'}")

@socketio.on('test_gift')
def handle_test_gift(data):
    """Handle test gifts from UI"""
    gift_type = data.get('type', '')
    value = data.get('value', 1)
    
    # Auto-enable test mode if sending test gifts
    if not tiktok_config['test_mode']:
        tiktok_config['test_mode'] = True
        tiktok_config['connected'] = True
        emit('tiktok_status', {'connected': True})
    
    if gift_type == 'rose' or gift_type == 'mawar':
        # Rose gift for female
        count = spawn_multiple_apples(value, 'female')
        emit('gift_received', {
            'team': 'female',
            'gift': '🌹 Mawar',
            'value': value,
            'apples': count
        })
        print(f"Rose gift: {count} apples for female")
    
    elif gift_type == 'tiktok_gift':
        # TikTok gift for male
        count = spawn_multiple_apples(value, 'male')
        emit('gift_received', {
            'team': 'male',
            'gift': '🎁 TikTok Gift',
            'value': value,
            'apples': count
        })
        print(f"TikTok gift: {count} apples for male")
    
    elif gift_type == 'jari_hati':
        # Jari Hati - spawn bomb
        if spawn_bomb():
            emit('gift_received', {
                'team': 'both',
                'gift': '🤟 Jari Hati',
                'value': 1,
                'bomb': 1
            })
            print("Jari Hati: bomb spawned")
    
    elif gift_type == 'nasi_padang':
        # Nasi Padang - spawn bomb
        if spawn_bomb():
            emit('gift_received', {
                'team': 'both',
                'gift': '🍚 Nasi Padang',
                'value': 1,
                'bomb': 1
            })
            print("Nasi Padang: bomb spawned")
    
    elif gift_type == 'like':
        # 1000 likes simulation
        apples, bombs = spawn_mixed_items(1000 * value)
        emit('gift_received', {
            'team': 'both',
            'gift': '❤️ Like',
            'value': value,
            'apples': apples,
            'bombs': bombs
        })
        print(f"Like: {apples} apples, {bombs} bombs")
    
    # Send updated game state
    emit('game_update', game_state)

@socketio.on('connect_tiktok')
def handle_connect_tiktok(data):
    """Connect to TikTok Live"""
    username = data.get('username', '')
    if username:
        tiktok_config['username'] = username
        
        # Start TikTok client in thread if not already running
        if not tiktok_config['thread'] or not tiktok_config['thread'].is_alive():
            tiktok_config['thread'] = threading.Thread(target=start_tiktok_client)
            tiktok_config['thread'].daemon = True
            tiktok_config['thread'].start()
            emit('tiktok_status', {'connected': True, 'message': f'Connecting to @{username}...'})
        else:
            emit('tiktok_status', {'connected': tiktok_config['connected'], 'message': 'Already connected'})

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/status')
def api_status():
    return {
        'game_active': game_state['game_active'],
        'tiktok_connected': tiktok_config['connected'],
        'test_mode': tiktok_config['test_mode'],
        'male_score': game_state['male_score'],
        'female_score': game_state['female_score'],
        'round': game_state['round']
    }

if __name__ == '__main__':
    # Start game loop
    game_thread = threading.Thread(target=game_loop)
    game_thread.daemon = True
    game_thread.start()
    
    # Spawn initial apples
    for _ in range(3):
        spawn_apple()
    
    print("=" * 50)
    print("🐍 TikTok Snake Battle Game Started!")
    print("=" * 50)
    print(f"Initial snake: {game_state['snake']['body']}")
    print(f"Initial apples: {game_state['apples']}")
    print(f"Test Mode: {'ON' if tiktok_config['test_mode'] else 'OFF'}")
    print("=" * 50)
    print("To connect TikTok Live:")
    print("1. Edit app.py and set your TikTok username")
    print("2. Or use the web interface to connect")
    print("=" * 50)
    
    # Run Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=8080, debug=True, allow_unsafe_werkzeug=True)
