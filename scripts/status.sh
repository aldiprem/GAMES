#!/bin/bash
# Script untuk mengecek status Flask App dan Bot Telegram

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}📊 Status Website Management + Bot Telegram${NC}"
echo -e "${BLUE}============================================${NC}"

# Pindah ke direktori utama
cd "$(dirname "$0")/.." || exit 1

# Cek proses Flask
FLASK_PID=$(ps aux | grep '[p]ython3 app.py' | awk '{print $2}')
if [ -n "$FLASK_PID" ]; then
    FLASK_CPU=$(ps -p $FLASK_PID -o %cpu | tail -1 | tr -d ' ')
    FLASK_MEM=$(ps -p $FLASK_PID -o %mem | tail -1 | tr -d ' ')
    FLASK_RUNTIME=$(ps -o etime= -p $FLASK_PID | tr -d ' ')
    echo -e "${GREEN}✅ Flask App: RUNNING${NC}"
    echo -e "   PID: $FLASK_PID"
    echo -e "   CPU: ${FLASK_CPU}% | MEM: ${FLASK_MEM}%"
    echo -e "   Runtime: $FLASK_RUNTIME"
else
    echo -e "${RED}❌ Flask App: STOPPED${NC}"
fi

# Cek proses Bot
BOT_PID=$(ps aux | grep '[p]ython3 b.py' | awk '{print $2}')
if [ -n "$BOT_PID" ]; then
    BOT_CPU=$(ps -p $BOT_PID -o %cpu | tail -1 | tr -d ' ')
    BOT_MEM=$(ps -p $BOT_PID -o %mem | tail -1 | tr -d ' ')
    BOT_RUNTIME=$(ps -o etime= -p $BOT_PID | tr -d ' ')
    echo -e "${PURPLE}✅ Telegram Bot: RUNNING${NC}"
    echo -e "   PID: $BOT_PID"
    echo -e "   CPU: ${BOT_CPU}% | MEM: ${BOT_MEM}%"
    echo -e "   Runtime: $BOT_RUNTIME"
else
    echo -e "${RED}❌ Telegram Bot: STOPPED${NC}"
fi

# Cek screen session
SCREEN_SESSION=$(screen -ls | grep website_bot)
if [ -n "$SCREEN_SESSION" ]; then
    echo -e "${GREEN}✅ Screen Session: ACTIVE${NC}"
    echo -e "   $SCREEN_SESSION"
else
    echo -e "${YELLOW}⚠️  Screen Session: NOT FOUND${NC}"
fi

# Cek port 8000
if command -v nc &> /dev/null; then
    if nc -z localhost 8000 2>/dev/null; then
        echo -e "${GREEN}✅ Port 8000: LISTENING${NC}"
    else
        echo -e "${RED}❌ Port 8000: CLOSED${NC}"
    fi
fi

echo -e "${BLUE}============================================${NC}"

# Cek database
echo -e "${YELLOW}📁 Database Status:${NC}"
DB_DIR="database"
if [ -d "$DB_DIR" ]; then
    USERS_DB="$DB_DIR/users.db"
    BOTS_DB="$DB_DIR/bots.db"
    STOK_DB="$DB_DIR/stok.db"
    GACHA_DB="$DB_DIR/gacha.db"
    
    [ -f "$USERS_DB" ] && echo -e "   ✅ users.db: OK" || echo -e "   ❌ users.db: MISSING"
    [ -f "$BOTS_DB" ] && echo -e "   ✅ bots.db: OK" || echo -e "   ❌ bots.db: MISSING"
    [ -f "$STOK_DB" ] && echo -e "   ✅ stok.db: OK" || echo -e "   ❌ stok.db: MISSING"
    [ -f "$GACHA_DB" ] && echo -e "   ✅ gacha.db: OK" || echo -e "   ❌ gacha.db: MISSING"
else
    echo -e "   ❌ Directory database tidak ditemukan"
fi

echo -e "${BLUE}============================================${NC}"