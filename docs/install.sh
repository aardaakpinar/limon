#!/usr/bin/env bash
#
# limon - tek komutla kurulum (Linux/macOS). git gerekmez.
#
#   curl -fsSL https://aardaakpinar.github.io/limon/install.sh | bash
#   curl -fsSL https://aardaakpinar.github.io/limon/install.sh | bash -s -- --extras claude
#
# Kodları ~/.limon/src altına indirir, sanal ortamı ~/.limon/venv içinde kurar ve
# `limon` komutunu ~/.local/bin'e bağlar. Aynı komutu tekrar çalıştırmak günceller.
# Sürüm: varsayılan olarak GitHub'daki SON SÜRÜM etiketi kurulur (yayın yoksa main dalı).
# Ortam değişkenleri: LIMON_HOME (varsayılan ~/.limon), LIMON_REF (etiket/dal, ör. v0.2.0 veya main),
#                     LIMON_URL (özel zip adresi)

set -euo pipefail

REPO="aardaakpinar/limon"
HOME_DIR="${LIMON_HOME:-$HOME/.limon}"

if [ -t 1 ]; then GREEN="\033[32m"; RED="\033[31m"; RESET="\033[0m"; else GREEN=""; RED=""; RESET=""; fi
info()  { printf "%b\n" "${GREEN}==>${RESET} $*"; }
error() { printf "%b\n" "${RED}HATA:${RESET} $*" >&2; }

PYTHON_BIN=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PYTHON_BIN="$c"; break; fi
done
[ -n "$PYTHON_BIN" ] || { error "Python 3.9+ bulunamadı. Önce Python'u kurun."; exit 1; }

# Hangi sürüm? LIMON_REF verilmediyse son yayınlanan etiketi bul, olmazsa main'e düş.
REF="${LIMON_REF:-}"
if [ -z "$REF" ] && [ -z "${LIMON_URL:-}" ]; then
  if command -v curl >/dev/null 2>&1; then
    REF="$(curl -fsSL -m 10 "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
      | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("tag_name",""))' 2>/dev/null || true)"
  fi
  REF="${REF:-main}"
fi
URL="${LIMON_URL:-https://github.com/$REPO/archive/$REF.zip}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

info "limon indiriliyor ($REPO@$REF)..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o "$TMP/limon.zip"
elif command -v wget >/dev/null 2>&1; then
  wget -q "$URL" -O "$TMP/limon.zip"
else
  error "curl veya wget gerekiyor."; exit 1
fi

# unzip'e bağımlı olmamak için Python'un zipfile modülünü kullan
"$PYTHON_BIN" - "$TMP/limon.zip" "$TMP/out" <<'PY'
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
PY

SRC_DIR="$(find "$TMP/out" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -f "$SRC_DIR/pyproject.toml" ] || { error "İndirilen arşiv beklenen yapıda değil."; exit 1; }

mkdir -p "$HOME_DIR"
rm -rf "$HOME_DIR/src"
mv "$SRC_DIR" "$HOME_DIR/src"
info "Kodlar yerleştirildi: $HOME_DIR/src"

# Asıl kurulumu depodaki install.sh yapar; kullanıcının argümanları aynen iletilir.
bash "$HOME_DIR/src/install.sh" --venv-dir "$HOME_DIR/venv" "$@"
