#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${LIMON_REPO_URL:-https://github.com/aardaakpinar/limon.git}"
INSTALL_DIR="${LIMON_INSTALL_DIR:-$HOME/.limon-cli}"
BIN_DIR="${LIMON_BIN_DIR:-$HOME/.local/bin}"

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "HATA: '$1' gerekli ama bulunamadi."
        exit 1
    fi
}

need_cmd git
need_cmd node
need_cmd npm

NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
if [ "${NODE_MAJOR}" -lt 18 ]; then
    echo "HATA: Node.js >= 18 gerekli. Mevcut surum: $(node -v)"
    exit 1
fi

echo "LiMON kurulumu basliyor..."
echo "Dizin: ${INSTALL_DIR}"

if [ -d "${INSTALL_DIR}/.git" ]; then
    git -C "${INSTALL_DIR}" fetch --depth 1 origin
    git -C "${INSTALL_DIR}" reset --hard origin/HEAD
else
    rm -rf "${INSTALL_DIR}"
    git clone --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"
npm install --omit=dev

# Try to register the CLI globally via npm (best effort)
set +e
npm link >/dev/null 2>&1
LINK_STATUS=$?
set -e

mkdir -p "${BIN_DIR}"
cat > "${BIN_DIR}/limon" <<EOF
#!/usr/bin/env bash
exec node "${INSTALL_DIR}/src/index.js" "\$@"
EOF
chmod +x "${BIN_DIR}/limon"

echo
echo "Kurulum tamamlandi."
echo "Komut: ${BIN_DIR}/limon"
if [ "${LINK_STATUS}" -eq 0 ]; then
    echo "npm link: OK"
else
    echo "npm link: Atlandi (wrapper kullaniliyor)."
fi

case ":$PATH:" in
    *":${BIN_DIR}:"*) ;;
    *)
        echo
        echo "PATH'te degil. Eklemek icin:"
        echo "  export PATH=\"${BIN_DIR}:\$PATH\""
        ;;
esac

echo
echo "Baslatmak icin: limon --setup"
