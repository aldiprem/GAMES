#!/bin/bash
# Script untuk menghentikan Flask App dan Bot Telegram

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}============================================${NC}"
echo -e "${YELLOW}🛑 Menghentikan Website Management + Bot Telegram${NC}"
echo -e "${YELLOW}============================================${NC}"

# Pindah ke direktori utama
cd "$(dirname "$0")/.." || exit 1

# Cari proses Flask (app.py)
FLASK_PID=$(ps aux | grep '[p]ython3 app.py' | awk '{print $2}')
# Cari proses Bot (b.py)
BOT_PID=$(ps aux | grep '[p]ython3 b.py' | awk '{print $2}')
# Cari proses screen (jika menggunakan screen)
SCREEN_PID=$(screen -ls | grep -o '[0-9]*\.website_bot' | cut -d'.' -f1)

# Hentikan Flask
if [ -n "$FLASK_PID" ]; then
    echo -e "${GREEN}📡 Menghentikan Flask App (PID: $FLASK_PID)...${NC}"
    kill -15 $FLASK_PID 2>/dev/null
    sleep 1
    if ps -p $FLASK_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Flask tidak berhenti, memaksa penghentian...${NC}"
        kill -9 $FLASK_PID 2>/dev/null
    fi
else
    echo -e "${YELLOW}⚠️  Tidak ada proses Flask yang berjalan${NC}"
fi

# Hentikan Bot
if [ -n "$BOT_PID" ]; then
    echo -e "${GREEN}🤖 Menghentikan Telegram Bot (PID: $BOT_PID)...${NC}"
    kill -15 $BOT_PID 2>/dev/null
    sleep 1
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Bot tidak berhenti, memaksa penghentian...${NC}"
        kill -9 $BOT_PID 2>/dev/null
    fi
else
    echo -e "${YELLOW}⚠️  Tidak ada proses Bot yang berjalan${NC}"
fi

# Hentikan screen session jika ada
if [ -n "$SCREEN_PID" ]; then
    echo -e "${GREEN}📱 Menghentikan screen session (PID: $SCREEN_PID)...${NC}"
    screen -S website_bot -X quit 2>/dev/null
    echo -e "${GREEN}✅ Screen session dihentikan${NC}"
fi

# Bersihkan file socket/session Telethon
echo -e "${YELLOW}🧹 Membersihkan file session...${NC}"
rm -f session_* 2>/dev/null

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Semua proses berhasil dihentikan${NC}"
echo -e "${GREEN}============================================${NC}"