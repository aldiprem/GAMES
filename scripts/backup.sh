#!/bin/bash
# Script untuk backup database

# Warna untuk output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/.." || exit 1

# Buat direktori backup
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Format tanggal
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}💾 Backup Database - $DATE${NC}"
echo -e "${BLUE}============================================${NC}"

# Cek apakah ada database
DB_COUNT=$(ls database/*.db 2>/dev/null | wc -l)
if [ "$DB_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ Tidak ada file database ditemukan${NC}"
    exit 1
fi

# Backup database
echo -e "${YELLOW}📦 Membuat archive: $BACKUP_FILE${NC}"
tar -czf "$BACKUP_FILE" database/*.db 2>/dev/null

if [ $? -eq 0 ]; then
    # Hitung ukuran
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup berhasil!${NC}"
    echo -e "   File: $BACKUP_FILE"
    echo -e "   Ukuran: $SIZE"
    
    # List isi backup
    echo -e "\n${YELLOW}📋 Database yang di-backup:${NC}"
    tar -tzf "$BACKUP_FILE" | while read -r file; do
        echo -e "   📁 $file"
    done
    
    # Hapus backup lama (lebih dari 7 hari)
    echo -e "\n${YELLOW}🧹 Membersihkan backup lama...${NC}"
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete
    echo -e "${GREEN}✅ Backup lama telah dibersihkan${NC}"
else
    echo -e "${RED}❌ Backup gagal${NC}"
fi

echo -e "${BLUE}============================================${NC}"