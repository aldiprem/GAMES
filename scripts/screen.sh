#!/bin/bash
# Script untuk mengelola screen session (production mode)

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SESSION_NAME="website_bot"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

show_help() {
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}📱 Screen Session Manager${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e "Penggunaan: ./screen.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Memulai session baru (Flask + Bot)"
    echo "  stop     - Menghentikan session"
    echo "  restart  - Merestart session"
    echo "  attach   - Melampirkan ke session (screen -r)"
    echo "  list     - Menampilkan daftar session"
    echo "  logs     - Melihat logs dari session"
    echo "  check    - Cek status session"
    echo ""
}

check_screen() {
    if ! command -v screen &> /dev/null; then
        echo -e "${RED}❌ Screen tidak terinstall. Menginstall...${NC}"
        apt update && apt install screen -y
    fi
}

start_session() {
    check_screen
    
    echo -e "${GREEN}📡 Memulai screen session: $SESSION_NAME${NC}"
    echo -e "${BLUE}📂 Project: $PROJECT_DIR${NC}"
    
    # Buat direktori logs
    mkdir -p "$PROJECT_DIR/logs"
    
    # Cek virtual environment
    if [ -d "$PROJECT_DIR/myenv" ]; then
        VENV_PATH="myenv"
    elif [ -d "$PROJECT_DIR/venv" ]; then
        VENV_PATH="venv"
    else
        echo -e "${RED}❌ Virtual environment tidak ditemukan!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Menggunakan virtual environment: $VENV_PATH${NC}"
    
    # Buat script runner dengan pengecekan yang lebih baik
    cat > "$PROJECT_DIR/scripts/runner.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
echo "📂 Working directory: \$(pwd)"

# Aktivasi virtual environment
if [ -d "$VENV_PATH" ]; then
    source $VENV_PATH/bin/activate
    echo "✅ Virtual environment activated: $VENV_PATH"
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Cek dependencies
echo "📦 Checking Flask..."
python3 -c "from flask import Flask; print('✅ Flask OK')" 2>/dev/null || echo "❌ Flask not found"

echo "📦 Checking Telethon..."
python3 -c "from telethon import TelegramClient; print('✅ Telethon OK')" 2>/dev/null || echo "❌ Telethon not found"

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping processes..."
    kill \$FLASK_PID 2>/dev/null
    kill \$BOT_PID 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT

# Jalankan Flask
echo "🚀 Memulai Flask App di port 8000..."
python3 app.py > "$PROJECT_DIR/logs/flask.log" 2>&1 &
FLASK_PID=\$!
echo "✅ Flask started with PID: \$FLASK_PID"

# Jalankan Bot
echo "🤖 Memulai Telegram Bot..."
python3 b.py > "$PROJECT_DIR/logs/bot.log" 2>&1 &
BOT_PID=\$!
echo "✅ Bot started with PID: \$BOT_PID"

echo "✅ Both processes are running in background"
echo "📝 Logs: $PROJECT_DIR/logs/"
echo "📊 Flask: http://localhost:8000"

# Wait for both processes
wait \$FLASK_PID \$BOT_PID
EOF

    chmod +x "$PROJECT_DIR/scripts/runner.sh"
    
    # Hentikan session lama jika ada
    screen -S $SESSION_NAME -X quit 2>/dev/null
    
    # Jalankan di screen dengan nama yang benar
    screen -dmS $SESSION_NAME bash -c "$PROJECT_DIR/scripts/runner.sh"
    
    sleep 3
    
    # Cek apakah session berhasil dimulai
    if screen -ls | grep -q "$SESSION_NAME"; then
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}✅ Session $SESSION_NAME berhasil dimulai!${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo -e "${YELLOW}📊 Flask App: http://localhost:8000${NC}"
        echo -e "${YELLOW}📝 Logs: ./screen.sh logs${NC}"
        echo -e "${YELLOW}📱 Attach: ./screen.sh attach${NC}"
        echo -e "${GREEN}============================================${NC}"
        
        # Tampilkan proses yang berjalan
        sleep 2
        echo -e "\n${BLUE}📋 Proses yang berjalan:${NC}"
        ps aux | grep -E "app.py|b.py" | grep -v grep
    else
        echo -e "${RED}❌ Gagal memulai session${NC}"
        echo -e "${YELLOW}📋 Daftar screen session saat ini:${NC}"
        screen -ls
    fi
}

stop_session() {
    echo -e "${YELLOW}🛑 Menghentikan screen session: $SESSION_NAME${NC}"
    
    # Cek apakah session ada
    if screen -ls | grep -q "$SESSION_NAME"; then
        screen -S $SESSION_NAME -X quit
        sleep 2
        
        if ! screen -ls | grep -q "$SESSION_NAME"; then
            echo -e "${GREEN}✅ Session $SESSION_NAME dihentikan${NC}"
            
            # Kill any remaining processes
            echo -e "${YELLOW}🔪 Membersihkan proses yang tersisa...${NC}"
            pkill -f "python3 app.py" 2>/dev/null
            pkill -f "python3 b.py" 2>/dev/null
            rm -f session_* 2>/dev/null
            
            echo -e "${GREEN}✅ Semua proses dibersihkan${NC}"
        else
            echo -e "${RED}❌ Gagal menghentikan session, memaksa dengan kill...${NC}"
            screen -S $SESSION_NAME -X kill
            sleep 1
            screen -wipe 2>/dev/null
        fi
    else
        echo -e "${YELLOW}⚠️  Session $SESSION_NAME tidak ditemukan${NC}"
        
        # Tetap bersihkan proses
        pkill -f "python3 app.py" 2>/dev/null
        pkill -f "python3 b.py" 2>/dev/null
        rm -f session_* 2>/dev/null
    fi
}

check_status() {
    echo -e "${BLUE}📊 Status Screen Session:${NC}"
    echo -e "${BLUE}============================================${NC}"
    
    # Cek screen session
    if screen -ls | grep -q "$SESSION_NAME"; then
        echo -e "${GREEN}✅ Session ACTIVE: $SESSION_NAME${NC}"
        screen -ls | grep "$SESSION_NAME"
    else
        echo -e "${RED}❌ Session INACTIVE: $SESSION_NAME${NC}"
    fi
    
    # Cek proses Flask
    FLASK_PID=$(ps aux | grep '[p]ython3 app.py' | awk '{print $2}')
    if [ -n "$FLASK_PID" ]; then
        FLASK_RUNTIME=$(ps -o etime= -p $FLASK_PID 2>/dev/null | tr -d ' ')
        echo -e "${GREEN}✅ Flask App: RUNNING (PID: $FLASK_PID, Runtime: $FLASK_RUNTIME)${NC}"
    else
        echo -e "${RED}❌ Flask App: STOPPED${NC}"
    fi
    
    # Cek proses Bot
    BOT_PID=$(ps aux | grep '[p]ython3 b.py' | awk '{print $2}')
    if [ -n "$BOT_PID" ]; then
        BOT_RUNTIME=$(ps -o etime= -p $BOT_PID 2>/dev/null | tr -d ' ')
        echo -e "${GREEN}✅ Telegram Bot: RUNNING (PID: $BOT_PID, Runtime: $BOT_RUNTIME)${NC}"
    else
        echo -e "${RED}❌ Telegram Bot: STOPPED${NC}"
    fi
    
    # Cek port 8000
    if command -v nc &> /dev/null; then
        if nc -z localhost 8000 2>/dev/null; then
            echo -e "${GREEN}✅ Port 8000: LISTENING${NC}"
        else
            echo -e "${RED}❌ Port 8000: CLOSED${NC}"
        fi
    fi
    
    # Cek logs
    if [ -f "$PROJECT_DIR/logs/flask.log" ]; then
        FLASK_LOG_SIZE=$(du -h "$PROJECT_DIR/logs/flask.log" | cut -f1)
        echo -e "${GREEN}📝 Flask log: $FLASK_LOG_SIZE${NC}"
    fi
    if [ -f "$PROJECT_DIR/logs/bot.log" ]; then
        BOT_LOG_SIZE=$(du -h "$PROJECT_DIR/logs/bot.log" | cut -f1)
        echo -e "${GREEN}📝 Bot log: $BOT_LOG_SIZE${NC}"
    fi
    
    echo -e "${BLUE}============================================${NC}"
}

case "$1" in
    start)
        start_session
        ;;
    stop)
        stop_session
        ;;
    restart)
        echo -e "${YELLOW}🔄 Merestart screen session: $SESSION_NAME${NC}"
        stop_session
        sleep 3
        start_session
        ;;
    attach)
        if screen -ls | grep -q "$SESSION_NAME"; then
            echo -e "${GREEN}📱 Melampirkan ke session: $SESSION_NAME${NC}"
            echo -e "${YELLOW}Tekan Ctrl+A kemudian D untuk keluar dari screen${NC}"
            sleep 2
            screen -r $SESSION_NAME
        else
            echo -e "${RED}❌ Session $SESSION_NAME tidak ditemukan${NC}"
            echo -e "Jalankan './screen.sh start' terlebih dahulu"
        fi
        ;;
    list)
        echo -e "${GREEN}📋 Daftar semua screen session:${NC}"
        screen -ls
        ;;
    logs)
        echo -e "${GREEN}📜 Logs dari session:${NC}"
        echo -e "${BLUE}============================================${NC}"
        if [ -f "$PROJECT_DIR/logs/flask.log" ]; then
            echo -e "${BLUE}=== Flask Logs (last 20 lines) ===${NC}"
            tail -20 "$PROJECT_DIR/logs/flask.log"
            echo ""
        fi
        if [ -f "$PROJECT_DIR/logs/bot.log" ]; then
            echo -e "${GREEN}=== Bot Logs (last 20 lines) ===${NC}"
            tail -20 "$PROJECT_DIR/logs/bot.log"
        fi
        if [ ! -f "$PROJECT_DIR/logs/flask.log" ] && [ ! -f "$PROJECT_DIR/logs/bot.log" ]; then
            echo -e "${YELLOW}⚠️  Tidak ada file log ditemukan${NC}"
        fi
        echo -e "${BLUE}============================================${NC}"
        ;;
    check|status)
        check_status
        ;;
    *)
        show_help
        ;;
esac