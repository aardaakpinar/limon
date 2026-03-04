#!/bin/bash

# 🍋 LiMON - Arch Linux Otomatik Kurulum Scripti
# Kullanım: sudo bash install.sh

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_banner() {
    clear
    echo -e "${YELLOW}"
    echo "  ██╗     ██╗███╗   ███╗ ██████╗ ███╗   ██╗"
    echo "  ██║     ██║████╗ ████║██╔═══██╗████╗  ██║"
    echo "  ██║     ██║██╔████╔██║██║   ██║██╔██╗ ██║"
    echo "  ██║     ██║██║╚██╔╝██║██║   ██║██║╚██╗██║"
    echo "  ███████╗██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║"
    echo "  ╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝"
    echo -e "${NC}"
    echo -e "${BLUE}  Arch Linux Kurulum Scripti${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}◆${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Root kontrol
if [ "$EUID" -ne 0 ]; then 
   log_error "Bu script root olarak çalıştırılmalıdır."
   echo "Kullanım: sudo bash install.sh"
   exit 1
fi

print_banner

# 1. Dependencies kontrol
log_info "Bağımlılıklar kontrol ediliyor..."
if ! command -v node &> /dev/null; then
    log_warn "Node.js bulunamadı. Yükleniyor..."
    pacman -Sy --noconfirm nodejs npm
else
    log_success "Node.js zaten yüklenmiş: $(node -v)"
fi

# 2. Dizin oluştur
log_info "Kurulum dizini hazırlanıyor..."
INSTALL_DIR="/opt/limon"
if [ -d "$INSTALL_DIR" ]; then
    log_warn "$INSTALL_DIR zaten var. Yedekleniyor..."
    mv "$INSTALL_DIR" "$INSTALL_DIR.backup.$(date +%s)"
fi
mkdir -p "$INSTALL_DIR"
log_success "Dizin oluşturuldu: $INSTALL_DIR"

# 3. Dosyaları kopyala
log_info "LiMON dosyaları kopyalanıyor..."
if [ -f "index.js" ]; then
    cp *.js "$INSTALL_DIR/"
    cp package.json "$INSTALL_DIR/" 2>/dev/null || true
    cp limon.service /etc/systemd/system/
    log_success "Dosyalar kopyalandı"
else
    log_error "LiMON dosyaları bu dizinde bulunamadı."
    log_info "Lütfen kurulum scriptini LiMON kaynak dizininde çalıştırın."
    exit 1
fi

# 4. Permissions
log_info "İzinler ayarlanıyor..."
chmod +x "$INSTALL_DIR/index.js"
chown -R root:root "$INSTALL_DIR"
log_success "İzinler ayarlandı"

# 5. Systemd setup
log_info "Systemd service kurulumu..."
systemctl daemon-reload
systemctl enable limon.service
log_success "Service etkinleştirildi"

# 6. Konfigürasyon oluştur
log_info "İlk konfigürasyon hazırlanıyor..."

# Config dizini
mkdir -p /root/.limon

# Eğer environment variables varsa config olarak kaydet
if [ -n "$LIMON_PROVIDER" ] || [ -n "$LIMON_API_KEY" ]; then
    log_info "Environment variables'dan config oluşturuluyor..."
    cat > /root/.limon/config.json <<EOF
{
  "provider": "${LIMON_PROVIDER:-claude}",
  "apiKey": "${LIMON_API_KEY:-}",
  "workDir": "${LIMON_WORK_DIR:-/opt/limon-workspace}",
  "securityEnabled": true
}
EOF
    log_success "Config kaydedildi"
else
    log_warn "LIMON_API_KEY environment variable bulunamadı."
    log_info "İlk çalıştırmada setup mekanizması devreye girecek."
fi

# 7. Workspace dizini
log_info "Workspace dizini oluşturuluyor..."
WORK_DIR="${LIMON_WORK_DIR:-/opt/limon-workspace}"
mkdir -p "$WORK_DIR"
chown -R root:root "$WORK_DIR"
log_success "Workspace: $WORK_DIR"

# 8. Log dizini
log_info "Log dizini hazırlanıyor..."
mkdir -p /var/log/limon
chown -R root:root /var/log/limon
log_success "Log dizini: /var/log/limon"

# 9. Seçenekli başlatma
echo ""
read -p "Şimdi LiMON'u başlatmak ister misiniz? [e/H] " -n 1 -r
echo
if [[ $REPLY =~ ^[Ee]$ ]]; then
    log_info "LiMON başlatılıyor..."
    systemctl start limon.service
    sleep 2
    systemctl status limon.service
else
    log_info "Başlangıç atlandı. Elle başlatmak için:"
    echo "    sudo systemctl start limon.service"
fi

echo ""
print_banner
log_success "Kurulum tamamlandı! 🍋"
echo ""
echo -e "${GREEN}Faydalı komutlar:${NC}"
echo "  ${BLUE}Başlat:${NC}      sudo systemctl start limon.service"
echo "  ${BLUE}Durdur:${NC}      sudo systemctl stop limon.service"
echo "  ${BLUE}Durum:${NC}       sudo systemctl status limon.service"
echo "  ${BLUE}Log:${NC}         sudo journalctl -u limon.service -f"
echo "  ${BLUE}Setup:${NC}       sudo systemctl start limon.service"
echo ""
echo -e "${YELLOW}İlk kez çalıştırırken setup soruları sorulacaktır.${NC}"
echo ""
