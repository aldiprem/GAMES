#!/bin/bash
# Script untuk merestart Flask App dan Bot Telegram

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}============================================${NC}"
echo -e "${YELLOW}🔄 Merestart Website Management + Bot Telegram${NC}"
echo -e "${YELLOW}============================================${NC}"

# Pindah ke direktori utama
cd "$(dirname "$0")" || exit 1

# Stop semua proses
echo -e "${YELLOW}🛑 Menghentikan proses yang berjalan...${NC}"
./stop.sh

# Tunggu 3 detik
echo -e "${YELLOW}⏳ Menunggu 3 detik...${NC}"
sleep 3

# Start semua proses
echo -e "${GREEN}🚀 Memulai ulang semua proses...${NC}"
./start.sh