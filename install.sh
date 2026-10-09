#!/usr/bin/env bash
#
# limon - Linux/macOS kurulum betiği
#
# Kullanım:
# ./install.sh                  -> .venv oluşturur, limon'u kurar ve `limon` komutunu ~/.local/bin'e bağlar
# ./install.sh --extras claude  -> sadece Claude SDK'sını kurar (openai, gemini, all de olur)
# ./install.sh --no-venv        -> venv oluşturmadan mevcut Python ortamına kurar
# ./install.sh --bin-dir DIR    -> komutu ~/.local/bin yerine DIR içine bağlar

set -euo pipefail

# --- Varsayılanlar ---------------------------------------------------------
EXTRAS="all"
VENV_DIR=".venv"
USE_VENV=1
BIN_DIR="$HOME/.local/bin"
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
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
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
    --bin-dir)
      BIN_DIR="${2:-$BIN_DIR}"
      shift 2
      ;;
    --bin-dir=*)
      BIN_DIR="${1#*=}"
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

  # Etkinleştirmeye (activate) gerek yok: doğrudan venv'in Python'unu kullanıyoruz.
  VENV_ABS="$(cd "$VENV_DIR" && pwd)"
  PYTHON_BIN="$VENV_ABS/bin/python"
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

# --- `limon` komutunu sanal ortamın dışında da kullanılabilir yap ---------------
if [ "$USE_VENV" -eq 1 ]; then
  LIMON_EXE="$VENV_ABS/bin/limon"
  LINK="$BIN_DIR/limon"
  mkdir -p "$BIN_DIR"
  if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
    warn "$LINK zaten var ve bir kısayol değil; dokunulmadı."
    warn "Komutu doğrudan şuradan çalıştırabilirsiniz: $LIMON_EXE"
  else
    ln -sf "$LIMON_EXE" "$LINK"
    info "Kısayol oluşturuldu: $LINK"
  fi

  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
      # PATH'e kalıcı olarak ekle (tekrar çalıştırılırsa çoğaltmaz)
      EXPORT_LINE="export PATH=\"$BIN_DIR:\$PATH\""
      case "$(basename "${SHELL:-}")" in
        zsh)  RC_FILES=("$HOME/.zshrc") ;;
        bash) RC_FILES=("$HOME/.bashrc" "$HOME/.bash_profile") ;;
        *)    RC_FILES=("$HOME/.profile") ;;
      esac
      for RC in "${RC_FILES[@]}"; do
        # .bash_profile yalnızca zaten varsa; yoksa oluşturup .bashrc'yi gölgelemeyelim
        if [ "$RC" = "$HOME/.bash_profile" ] && [ ! -e "$RC" ]; then continue; fi
        if ! grep -qsF "$BIN_DIR" "$RC"; then
          printf '\n# limon\n%s\n' "$EXPORT_LINE" >> "$RC"
          info "$BIN_DIR PATH'e eklendi: $RC"
        fi
      done
      NEED_RELOAD=1
      ;;
  esac
fi

echo
info "${BOLD}Kurulum tamamlandı!${RESET}"
if [ "${NEED_RELOAD:-0}" -eq 1 ]; then
  warn "PATH değişikliğinin etkili olması için ${BOLD}yeni bir terminal açın${RESET} ya da şunu çalıştırın:"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi
echo "Kullanmaya başlamak için:"
echo "  limon config     # sağlayıcı / model / API anahtarı ayarla"
echo "  limon            # etkileşimli REPL'i başlat"
