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
    echo -e "${GREEN}Penggunaan: ./screen.sh [command]${NC}"
    echo ""
    echo "Commands:"
    echo "  start    - Memulai session baru (Flask + Bot)"
    echo "  stop     - Menghentikan session"
    echo "  restart  - Merestart session"
    echo "  attach   - Melampirkan ke session (screen -r)"
    echo "  list     - Menampilkan daftar session"
    echo "  logs     - Melihat logs dari session"
    echo ""
}

start_session() {
    echo -e "${GREEN}📡 Memulai screen session: $SESSION_NAME${NC}"
    echo -e "${BLUE}📂 Project: $PROJECT_DIR${NC}"
    
    # Buat direktori logs
    mkdir -p "$PROJECT_DIR/logs"
    
    # Buat script runner
    cat > "$PROJECT_DIR/scripts/runner.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
source venv/bin/activate
echo "🚀 Memulai Flask App di port 8000..."
python3 app.py > "$PROJECT_DIR/logs/flask.log" 2>&1 &
FLASK_PID=\$!
echo "🤖 Memulai Telegram Bot..."
python3 b.py > "$PROJECT_DIR/logs/bot.log" 2>&1
EOF
    chmod +x "$PROJECT_DIR/scripts/runner.sh"
    
    # Jalankan di screen
    screen -dmS $SESSION_NAME bash -c "$PROJECT_DIR/scripts/runner.sh"
    
    sleep 2
    if screen -ls | grep -q $SESSION_NAME; then
        echo -e "${GREEN}✅ Session $SESSION_NAME dimulai${NC}"
        echo -e "${YELLOW}📊 Flask: http://localhost:8000${NC}"
        echo -e "${YELLOW}📝 Logs: ./logs.sh flask|bot${NC}"
    else
        echo -e "${RED}❌ Gagal memulai session${NC}"
    fi
}

case "$1" in
    start)
        start_session
        ;;
    stop)
        echo -e "${YELLOW}🛑 Menghentikan screen session: $SESSION_NAME${NC}"
        screen -S $SESSION_NAME -X quit
        sleep 1
        if ! screen -ls | grep -q $SESSION_NAME; then
            echo -e "${GREEN}✅ Session $SESSION_NAME dihentikan${NC}"
            # Kill any remaining processes
            pkill -f "python3 app.py" 2>/dev/null
            pkill -f "python3 b.py" 2>/dev/null
        else
            echo -e "${RED}❌ Gagal menghentikan session${NC}"
        fi
        ;;
    restart)
        echo -e "${YELLOW}🔄 Merestart screen session: $SESSION_NAME${NC}"
        $0 stop
        sleep 3
        $0 start
        ;;
    attach)
        echo -e "${GREEN}📱 Melampirkan ke session: $SESSION_NAME${NC}"
        echo -e "${YELLOW}Tekan Ctrl+A kemudian D untuk keluar dari screen${NC}"
        sleep 2
        screen -r $SESSION_NAME
        ;;
    list)
        echo -e "${GREEN}📋 Daftar screen session:${NC}"
        screen -ls
        ;;
    logs)
        echo -e "${GREEN}📜 Logs dari session:${NC}"
        if [ -f "$PROJECT_DIR/logs/flask.log" ]; then
            echo -e "${BLUE}=== Flask Logs (last 20 lines) ===${NC}"
            tail -20 "$PROJECT_DIR/logs/flask.log"
        fi
        if [ -f "$PROJECT_DIR/logs/bot.log" ]; then
            echo -e "${GREEN}=== Bot Logs (last 20 lines) ===${NC}"
            tail -20 "$PROJECT_DIR/logs/bot.log"
        fi
        ;;
    *)
        show_help
        ;;
esac