#!/bin/bash
# Script untuk update dependencies dan restart

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/.." || exit 1

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}🔄 Update Dependencies${NC}"
echo -e "${BLUE}============================================${NC}"

# Cek virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Membuat virtual environment...${NC}"
    python3 -m venv venv
fi

# Aktifkan virtual environment
source venv/bin/activate

# Update pip
echo -e "${YELLOW}📦 Mengupdate pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1

# Install/update dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Menginstall/update dependencies...${NC}"
    pip install -r requirements.txt --upgrade > /dev/null 2>&1
    echo -e "${GREEN}✅ Dependencies terupdate${NC}"
    
    # Tampilkan versi
    echo -e "\n${YELLOW}📋 Versi packages:${NC}"
    pip list --format=freeze | grep -E "Flask|python-dotenv|telethon|requests|beautifulsoup4|aiohttp"
else
    echo -e "${RED}❌ File requirements.txt tidak ditemukan${NC}"
    exit 1
fi

# Restart services
echo -e "\n${YELLOW}🔄 Merestart services...${NC}"
./scripts/restart.sh

echo -e "${BLUE}============================================${NC}"