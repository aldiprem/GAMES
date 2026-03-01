#!/bin/bash
# Script untuk melihat logs Flask App dan Bot Telegram

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Pindah ke direktori utama
cd "$(dirname "$0")/.." || exit 1

# Buat direktori logs jika belum ada
mkdir -p logs

show_help() {
    echo -e "${GREEN}Penggunaan: ./logs.sh [option]${NC}"
    echo ""
    echo "Options:"
    echo "  flask     - Lihat logs Flask App"
    echo "  bot       - Lihat logs Telegram Bot"
    echo "  all       - Lihat semua logs (tail -f)"
    echo "  clear     - Hapus semua logs"
    echo "  help      - Tampilkan bantuan ini"
    echo ""
}

case "$1" in
    flask)
        echo -e "${BLUE}📡 Flask App Logs:${NC}"
        if [ -f "logs/flask.log" ]; then
            tail -f logs/flask.log
        else
            echo -e "${YELLOW}⚠️  File log flask tidak ditemukan${NC}"
        fi
        ;;
    bot)
        echo -e "${GREEN}🤖 Telegram Bot Logs:${NC}"
        if [ -f "logs/bot.log" ]; then
            tail -f logs/bot.log
        else
            echo -e "${YELLOW}⚠️  File log bot tidak ditemukan${NC}"
        fi
        ;;
    all)
        echo -e "${BLUE}📡 Semua Logs (Flask + Bot):${NC}"
        if [ -f "logs/flask.log" ] && [ -f "logs/bot.log" ]; then
            tail -f logs/flask.log logs/bot.log
        else
            echo -e "${YELLOW}⚠️  File log tidak lengkap${NC}"
        fi
        ;;
    clear)
        echo -e "${YELLOW}🧹 Menghapus semua logs...${NC}"
        rm -f logs/*.log
        echo -e "${GREEN}✅ Logs telah dihapus${NC}"
        ;;
    *)
        show_help
        ;;
esac