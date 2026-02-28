let socket;
let gridElement;
let gameState = null;
let testMode = true;
let lastUpdateTime = 0;
let logCounter = 0;

// Tambahkan tracking arah untuk animasi kepala
let lastDirection = 'RIGHT';

window.onload = function() {
    socket = io({
        transports: ['websocket'],
        upgrade: false,
        reconnection: true,
        reconnectionAttempts: 10,
        reconnectionDelay: 1000
    });
    
    gridElement = document.getElementById('game-grid');
    
    createGrid();
    
    socket.on('connect', function() {
        console.log('%c🔥 CONNECTED TO SERVER', 'color: green; font-size: 16px');
        updateConnectionStatus(true);
        addLog('System', '🟢 Connected to server');
    });
    
    socket.on('disconnect', function() {
        console.log('%c❌ DISCONNECTED', 'color: red; font-size: 16px');
        updateConnectionStatus(false);
        addLog('System', '🔴 Disconnected from server');
    });
    
    socket.on('game_update', function(state) {
        gameState = state;
        updateGame();
        
        // Log pergerakan
        if (state.snake && state.snake.body && state.snake.body.length > 0) {
            console.log(`🐍 HEAD: (${state.snake.body[0][0]},${state.snake.body[0][1]}) ➡️ ${state.snake.direction}`);
            lastDirection = state.snake.direction;
        }
    });
    
    socket.on('tiktok_status', function(data) {
        updateTikTokStatus(data.connected);
        if (data.connected) {
            addLog('TikTok', '🟢 Connected to TikTok Live');
        } else {
            addLog('TikTok', '🔴 Disconnected from TikTok');
        }
    });
    
    socket.on('gift_received', function(data) {
        addGiftLog(data);
        showGiftAnimation(data);
    });
    
    socket.on('game_over', function(data) {
        showGameOver(data.winner);
        addLog('Game', `🏆 Game Over: ${data.winner === 'male' ? 'Laki-laki' : 'Perempuan'} menang!`);
    });
    
    socket.on('tiktok_event', function(data) {
        if (data.type === 'comment') {
            addLog('💬 Comment', `${data.user}: ${data.message}`);
        } else if (data.type === 'follow') {
            addLog('👥 Follow', `${data.user} followed!`);
            showFloatingEmoji('👥');
        } else if (data.type === 'share') {
            addLog('🔄 Share', `${data.user} shared!`);
            showFloatingEmoji('🔄');
        }
    });
    
    setTimeout(() => {
        socket.emit('get_game_state');
    }, 500);
    
    // Update lebih sering untuk animasi smooth
    setInterval(() => {
        if (socket && socket.connected) {
            socket.emit('get_game_state');
        }
    }, 100);
};

function updateConnectionStatus(connected) {
    let statusEl = document.getElementById('connection-status');
    if (!statusEl) {
        statusEl = document.createElement('span');
        statusEl.id = 'connection-status';
        statusEl.style.marginLeft = '5px';
        statusEl.style.fontSize = '0.7rem';
        document.querySelector('.connection-controls').appendChild(statusEl);
    }
    
    if (connected) {
        statusEl.innerHTML = '🟢 Online';
        statusEl.style.color = '#4CAF50';
    } else {
        statusEl.innerHTML = '🔴 Offline';
        statusEl.style.color = '#f44336';
    }
}

function addLog(type, message) {
    const logMessages = document.getElementById('log-messages');
    const placeholder = logMessages.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();
    
    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    logItem.textContent = `[${new Date().toLocaleTimeString()}] ${type}: ${message}`;
    
    logMessages.appendChild(logItem);
    
    while (logMessages.children.length > 5) {
        logMessages.removeChild(logMessages.firstChild);
    }
}

function showFloatingEmoji(emoji) {
    const animDiv = document.createElement('div');
    animDiv.style.position = 'fixed';
    animDiv.style.left = Math.random() * 80 + 10 + '%';
    animDiv.style.top = '50%';
    animDiv.style.transform = 'translate(-50%, -50%)';
    animDiv.style.fontSize = '3rem';
    animDiv.style.zIndex = '9999';
    animDiv.style.animation = 'floatUp 2s ease-out forwards';
    animDiv.style.pointerEvents = 'none';
    animDiv.style.textShadow = '0 0 20px white';
    animDiv.innerHTML = emoji;
    
    document.body.appendChild(animDiv);
    setTimeout(() => {
        document.body.removeChild(animDiv);
    }, 2000);
}

function createGrid() {
    gridElement.innerHTML = '';
    for (let y = 0; y < 10; y++) {
        for (let x = 0; x < 15; x++) {
            const cell = document.createElement('div');
            cell.className = 'grid-cell';
            cell.id = `cell-${x}-${y}`;
            cell.setAttribute('data-x', x);
            cell.setAttribute('data-y', y);
            
            // Border akan diatur oleh CSS berdasarkan data-x
            gridElement.appendChild(cell);
        }
    }
}

function updateGame() {
    if (!gameState) return;
    
    // RESET SEMUA CELL
    document.querySelectorAll('.grid-cell').forEach(cell => {
        cell.innerHTML = '';
        cell.className = 'grid-cell';
        cell.style.background = '';
        cell.style.color = '';
        cell.style.transform = '';
        
        // Set data-x untuk CSS border
        const x = parseInt(cell.getAttribute('data-x'));
        cell.setAttribute('data-x', x);
    });
    
    // GAMBAR BOMBS
    if (gameState.bombs && gameState.bombs.length > 0) {
        gameState.bombs.forEach(bomb => {
            const cell = document.getElementById(`cell-${bomb.x}-${bomb.y}`);
            if (cell) {
                cell.innerHTML = '💣';
                cell.classList.add('bomb');
            }
        });
    }
    
    // GAMBAR APPLES
    if (gameState.apples && gameState.apples.length > 0) {
        gameState.apples.forEach(apple => {
            const cell = document.getElementById(`cell-${apple.x}-${apple.y}`);
            if (cell) {
                cell.innerHTML = '🍎';
                cell.classList.add('apple');
                
                if (apple.team === 'female') {
                    cell.classList.add('female-apple');
                } else if (apple.team === 'male') {
                    cell.classList.add('male-apple');
                }
            }
        });
    }
    
    // ===== PERBAIKAN SNAKE - ANIMASI LEBIH HIDUP =====
    if (gameState.snake && gameState.snake.body && gameState.snake.body.length > 0) {
        const body = gameState.snake.body;
        const direction = gameState.snake.direction;
        
        body.forEach((segment, index) => {
            const [x, y] = segment;
            const cell = document.getElementById(`cell-${x}-${y}`);
            
            if (cell) {
                if (index === 0) {
                    // KEPALA - dengan animasi dan arah
                    cell.classList.add('snake-head');
                    
                    // Tambah emoji sesuai arah
                    if (direction === 'RIGHT') {
                        cell.innerHTML = '▶️🐍';
                    } else if (direction === 'LEFT') {
                        cell.innerHTML = '🐍◀️';
                    } else {
                        cell.innerHTML = '🐍';
                    }
                    
                    cell.style.zIndex = '20';
                    
                    // Animasi tambahan
                    cell.style.animation = 'snakeHeadGlow 0.3s infinite alternate, snakeMove 0.2s ease';
                    
                } else {
                    // BADAN - dengan efek gradien
                    cell.classList.add('snake-body');
                    
                    // Badan pertama (leher) sedikit berbeda
                    if (index === 1) {
                        cell.style.background = 'linear-gradient(135deg, #5cb85c, #4CAF50)';
                        cell.style.borderRadius = '40%';
                    } else {
                        cell.style.background = '#4CAF50';
                    }
                    
                    cell.style.animation = 'snakeBodyPulse 0.5s infinite alternate';
                }
            }
        });
        
        // Efek trail untuk ekor
        if (body.length > 2) {
            const tail = body[body.length - 1];
            const tailCell = document.getElementById(`cell-${tail[0]}-${tail[1]}`);
            if (tailCell) {
                tailCell.style.opacity = '0.8';
            }
        }
    }
    
    // UPDATE SCORE
    document.getElementById('male-score').textContent = gameState.male_score || 0;
    document.getElementById('female-score').textContent = gameState.female_score || 0;
    document.getElementById('round').textContent = gameState.round || 1;
}

function updateTikTokStatus(connected) {
    const statusEl = document.getElementById('tiktok-status');
    const testBtn = document.getElementById('test-btn');
    const statusText = document.getElementById('tiktok-connection-status');
    
    if (connected) {
        statusEl.innerHTML = '🟢';
        statusEl.classList.add('status-connected');
        testMode = true;
        testBtn.textContent = '🧪 TEST MODE ON';
        testBtn.classList.add('active');
        if (statusText) statusText.textContent = '✅ Live Connected';
        console.log('%c🎮 TEST MODE: ON', 'color: yellow; font-size: 14px');
    } else {
        statusEl.innerHTML = '🔴';
        statusEl.classList.remove('status-connected');
        testMode = false;
        testBtn.textContent = '🧪 TEST MODE OFF';
        testBtn.classList.remove('active');
        if (statusText) statusText.textContent = '🔴 Test Mode';
        console.log('%c🎮 TEST MODE: OFF', 'color: gray; font-size: 14px');
    }
}

function addGiftLog(data) {
    const logMessages = document.getElementById('log-messages');
    const placeholder = logMessages.querySelector('.log-placeholder');
    if (placeholder) placeholder.remove();
    
    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    
    let message = '';
    let emoji = '';
    
    if (data.team === 'female') {
        emoji = '👩';
        message = `${emoji} ${data.gift}: +${data.apples || 0} apel`;
        if (data.user) message += ` dari @${data.user}`;
        logItem.style.borderLeftColor = '#e84393';
    } else if (data.team === 'male') {
        emoji = '👨';
        message = `${emoji} ${data.gift}: +${data.apples || 0} apel`;
        if (data.user) message += ` dari @${data.user}`;
        logItem.style.borderLeftColor = '#3498db';
    } else {
        if (data.bomb) {
            emoji = '💣';
            message = `${emoji} ${data.gift}: +${data.bomb} bomb`;
            logItem.style.borderLeftColor = '#e74c3c';
        } else {
            emoji = '❤️';
            message = `${emoji} ${data.gift}: ${data.apples || 0} apel, ${data.bombs || 0} bomb`;
            logItem.style.borderLeftColor = '#f1c40f';
        }
        if (data.user) message += ` dari @${data.user}`;
    }
    
    logItem.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logMessages.appendChild(logItem);
    
    while (logMessages.children.length > 5) {
        logMessages.removeChild(logMessages.firstChild);
    }
}

function showGiftAnimation(data) {
    const animDiv = document.createElement('div');
    animDiv.style.position = 'fixed';
    animDiv.style.left = '50%';
    animDiv.style.top = '50%';
    animDiv.style.transform = 'translate(-50%, -50%)';
    animDiv.style.fontSize = '5rem';
    animDiv.style.zIndex = '9999';
    animDiv.style.animation = 'giftPopup 1s ease-out forwards';
    animDiv.style.pointerEvents = 'none';
    animDiv.style.textShadow = '0 0 20px white';
    animDiv.style.fontWeight = 'bold';
    
    if (data.team === 'female') {
        animDiv.innerHTML = '👩 +' + (data.apples || 0);
        animDiv.style.color = '#e84393';
        animDiv.style.textShadow = '0 0 30px #e84393';
    } else if (data.team === 'male') {
        animDiv.innerHTML = '👨 +' + (data.apples || 0);
        animDiv.style.color = '#3498db';
        animDiv.style.textShadow = '0 0 30px #3498db';
    } else if (data.bomb) {
        animDiv.innerHTML = '💣';
        animDiv.style.color = '#e74c3c';
        animDiv.style.textShadow = '0 0 30px #e74c3c';
    } else {
        animDiv.innerHTML = '❤️ +' + ((data.apples || 0) + (data.bombs || 0));
        animDiv.style.color = '#f1c40f';
        animDiv.style.textShadow = '0 0 30px #f1c40f';
    }
    
    document.body.appendChild(animDiv);
    setTimeout(() => {
        document.body.removeChild(animDiv);
    }, 1000);
}

function showGameOver(winner) {
    const overlay = document.getElementById('game-overlay');
    const message = document.getElementById('winner-message');
    
    if (winner === 'male') {
        message.innerHTML = '👨 TEAM LAKI-LAKI MENANG! 👨';
        message.style.color = '#3498db';
    } else {
        message.innerHTML = '👩 TEAM PEREMPUAN MENANG! 👩';
        message.style.color = '#e84393';
    }
    
    overlay.classList.remove('hidden');
    console.log('%c🏆 GAME OVER: ' + message.innerHTML, 'color: gold; font-size: 20px');
}

// USER FUNCTIONS
function toggleTikTokTest() {
    socket.emit('toggle_tiktok_test');
    addLog('System', testMode ? '🔴 Test Mode OFF' : '🟢 Test Mode ON');
}

function sendTestGift(type, value) {
    console.log('%c📦 SENDING GIFT: ' + type + ' x' + value, 'color: cyan');
    socket.emit('test_gift', { type: type, value: value });
    addLog('Test', `📦 Sending ${type} x${value}`);
}

function resetGame() {
    console.log('%c🔄 RESETTING GAME', 'color: yellow');
    socket.emit('reset_game');
    document.getElementById('game-overlay').classList.add('hidden');
    addLog('System', '🔄 Game reset');
}

function connectTikTok() {
    const username = document.getElementById('tiktok-username').value.trim();
    if (username) {
        socket.emit('connect_tiktok', { username: username });
        addLog('TikTok', `🔌 Connecting to @${username}...`);
    } else {
        alert('Masukkan username TikTok');
    }
}

// CSS ANIMATION tambahan
const style = document.createElement('style');
style.textContent = `
    @keyframes giftPopup {
        0% { 
            opacity: 1; 
            transform: translate(-50%, -50%) scale(1);
        }
        50% {
            transform: translate(-50%, -50%) scale(1.5);
        }
        100% { 
            opacity: 0; 
            transform: translate(-50%, -150%) scale(2);
        }
    }
    
    @keyframes floatUp {
        0% { 
            opacity: 1; 
            transform: translate(-50%, -50%) scale(1);
        }
        100% { 
            opacity: 0; 
            transform: translate(-50%, -200%) scale(1.5);
        }
    }
`;
document.head.appendChild(style);
