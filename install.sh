#!/usr/bin/env bash
#
# limon - Linux/macOS kolay kurulum betiği
#
# Kullanım:
# ./install.sh                 -> .venv oluşturur ve tüm sağlayıcıları kurar (varsayılan)
# ./install.sh --extras all    -> tüm sağlayıcı SDK'larını kurar
# ./install.sh --extras claude -> sadece Claude SDK'sını kurar
# ./install.sh --extras openai -> sadece OpenAI SDK'sını kurar
# ./install.sh --extras gemini -> sadece Gemini SDK'sını kurar

set -euo pipefail

# --- Varsayılanlar ---------------------------------------------------------
EXTRAS="all"
VENV_DIR=".venv"
USE_VENV=1
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# --- Renkli çıktı yardımcıları ---------------------------------------------
if [ -t 1 ]; then
  BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

info()  { printf "%b\n" "${GREEN}==>${RESET} $*"; }
warn()  { printf "%b\n" "${YELLOW}==>${RESET} $*"; }
error() { printf "%b\n" "${RED}HATA:${RESET} $*" >&2; }

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
}

# --- Argümanları ayrıştır ----------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --extras)
      EXTRAS="${2:-}"
      shift 2
      ;;
    --extras=*)
      EXTRAS="${1#*=}"
      shift
      ;;
    --venv-dir)
      VENV_DIR="${2:-.venv}"
      shift 2
      ;;
    --venv-dir=*)
      VENV_DIR="${1#*=}"
      shift
      ;;
    --no-venv)
      USE_VENV=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      error "Bilinmeyen argüman: $1"
      usage
      exit 1
      ;;
  esac
done

cd "$SCRIPT_DIR"

# --- Python kontrolü ---------------------------------------------------------
PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  error "Python 3.9+ bulunamadı. Lütfen Python'u kurup tekrar deneyin."
  exit 1
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
info "Python bulundu: $PYTHON_BIN (v$PY_VERSION)"

REQ_MAJOR=3
REQ_MINOR=9
PY_MAJOR="$(echo "$PY_VERSION" | cut -d. -f1)"
PY_MINOR="$(echo "$PY_VERSION" | cut -d. -f2)"
if [ "$PY_MAJOR" -lt "$REQ_MAJOR" ] || { [ "$PY_MAJOR" -eq "$REQ_MAJOR" ] && [ "$PY_MINOR" -lt "$REQ_MINOR" ]; }; then
  error "limon için Python >= 3.9 gerekiyor, bulunan: $PY_VERSION"
  exit 1
fi

# --- Sanal ortam ------------------------------------------------------------
if [ "$USE_VENV" -eq 1 ]; then
  if [ -d "$VENV_DIR" ]; then
    info "Mevcut sanal ortam kullanılıyor: $VENV_DIR"
  else
    info "Sanal ortam oluşturuluyor: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
  PYTHON_BIN="python"
  info "Sanal ortam etkinleştirildi."
else
  warn "--no-venv verildi; paketler mevcut Python ortamına kurulacak."
fi

# --- pip güncelle -------------------------------------------------------------
info "pip güncelleniyor..."
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null

# --- Kurulum ------------------------------------------------------------------
if [ -n "$EXTRAS" ]; then
  info "limon kuruluyor (extras: $EXTRAS)..."
  "$PYTHON_BIN" -m pip install -e ".[$EXTRAS]"
else
  info "limon kuruluyor (temel bağımlılıklar)..."
  "$PYTHON_BIN" -m pip install -e "."
fi

echo
info "${BOLD}Kurulum tamamlandı!${RESET}"
if [ "$USE_VENV" -eq 1 ]; then
  echo "Sanal ortamı etkinleştirmek için:"
  echo "  source $VENV_DIR/bin/activate"
fi
echo "Kullanmaya başlamak için:"
echo "  limon config     # sağlayıcı / model / API anahtarı ayarla"
echo "  limon            # etkileşimli REPL'i başlat"
