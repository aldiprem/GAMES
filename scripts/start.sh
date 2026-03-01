#!/bin/bash
# Script untuk menjalankan Flask App dan Bot Telegram secara bersamaan

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🚀 Memulai Website Management + Bot Telegram${NC}"
echo -e "${GREEN}============================================${NC}"

# Pindah ke direktori utama
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

echo -e "${CYAN}📂 Project Directory: $PROJECT_DIR${NC}"

# Cek apakah Python sudah terinstall
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 tidak ditemukan. Silakan install Python3 terlebih dahulu.${NC}"
    exit 1
fi

# Cek virtual environment
if [ ! -d "myenv" ]; then
    echo -e "${YELLOW}📦 Membuat virtual environment...${NC}"
    python3 -m venv myenv
fi

# Aktivasi virtual environment
echo -e "${YELLOW}🔌 Mengaktifkan virtual environment...${NC}"
source myenv/bin/activate

# Cek dan install dependencies
echo -e "${YELLOW}📦 Memeriksa dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    # Hapus baris curl dari requirements.txt jika ada
    sed -i '/curl/d' requirements.txt
    
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dependencies terinstall${NC}"
    else
        echo -e "${RED}❌ Gagal install dependencies${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ File requirements.txt tidak ditemukan${NC}"
    exit 1
fi

# Function untuk menjalankan Flask
run_flask() {
    echo -e "${BLUE}📡 Menjalankan Flask App di port 8000...${NC}"
    python3 app.py
}

# Function untuk menjalankan Bot
run_bot() {
    echo -e "${PURPLE}🤖 Menjalankan Telegram Bot (b.py)...${NC}"
    python3 b.py
}

# Trap untuk menangani interrupt
trap 'echo -e "\n${RED}🛑 Menghentikan semua proses...${NC}"; kill $(jobs -p) 2>/dev/null; exit' INT TERM

# Jalankan kedua proses
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Semua proses dimulai!${NC}"
echo -e "${CYAN}📊 Flask App: http://localhost:8000${NC}"
echo -e "${CYAN}🤖 Bot Telegram: Running${NC}"
echo -e "${YELLOW}⚠️  Tekan Ctrl+C untuk menghentikan semua proses${NC}"
echo -e "${GREEN}============================================${NC}"

# Jalankan Flask di background
run_flask &
FLASK_PID=$!

# Jalankan Bot di foreground
run_bot

# Tunggu proses selesai
wait $FLASK_PID