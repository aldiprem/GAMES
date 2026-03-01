#!/bin/bash
# Script untuk membuat semua script dapat dieksekusi

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🔧 Membuat semua script dapat dieksekusi...${NC}"
echo -e "${GREEN}============================================${NC}"

SCRIPTS=(
    "start.sh"
    "stop.sh"
    "restart.sh"
    "status.sh"
    "logs.sh"
    "screen.sh"
    "make_executable.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        echo -e "${GREEN}✅ $script${NC}"
    else
        echo -e "${YELLOW}⚠️  $script tidak ditemukan${NC}"
    fi
done

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Selesai! Semua script sekarang dapat dieksekusi.${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Gunakan:"
echo -e "  ${YELLOW}./start.sh${NC}   - Untuk menjalankan Flask + Bot (foreground)"
echo -e "  ${YELLOW}./stop.sh${NC}    - Untuk menghentikan semua proses"
echo -e "  ${YELLOW}./status.sh${NC}  - Untuk mengecek status"
echo -e "  ${YELLOW}./restart.sh${NC} - Untuk merestart"
echo -e "  ${YELLOW}./logs.sh${NC}    - Untuk melihat logs"
echo -e "  ${YELLOW}./screen.sh${NC}  - Untuk production mode (screen)"