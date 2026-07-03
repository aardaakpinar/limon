#!/usr/bin/env bash
set -euo pipefail

# Simple installer for the project.
# Creates a virtual environment, upgrades pip/setuptools/wheel, and installs the package.
# Usage: ./install.sh [--extras all|openai|gemini|claude] [--no-venv]

VENV_DIR=".venv"
NO_VENV=0
EXTRAS=""

# Try to install Python on Unix-like systems when missing.
install_python_unix() {
  echo "Attempting to install Python via system package manager..."
  uname_s=$(uname -s || true)
  if [[ "$uname_s" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      echo "Homebrew found — installing python via brew..."
      brew update || true
      brew install python
      return $?
    else
      echo "Homebrew not found. Please install Homebrew or Python manually." >&2
      return 1
    fi
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "Using apt-get (Debian/Ubuntu)..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip
    return $?
  elif command -v dnf >/dev/null 2>&1; then
    echo "Using dnf (Fedora/CentOS)..."
    sudo dnf install -y python3 python3-venv python3-pip
    return $?
  elif command -v yum >/dev/null 2>&1; then
    echo "Using yum..."
    sudo yum install -y python3
    return $?
  elif command -v pacman >/dev/null 2>&1; then
    echo "Using pacman (Arch)..."
    sudo pacman -Sy --noconfirm python
    return $?
  elif command -v apk >/dev/null 2>&1; then
    echo "Using apk (Alpine)..."
    sudo apk add python3 py3-pip
    return $?
  elif command -v zypper >/dev/null 2>&1; then
    echo "Using zypper (openSUSE)..."
    sudo zypper install -y python3
    return $?
  else
    echo "No supported package manager found. Please install Python manually." >&2
    return 1
  fi
}

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --no-venv)
      NO_VENV=1
      shift
      ;;
    --extras)
      EXTRAS="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--extras all|openai|gemini|claude] [--no-venv]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--extras all|openai|gemini|claude] [--no-venv]"
      exit 1
      ;;
  esac
done

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "Python not found. Will try to install Python 3 automatically..." >&2
  if install_python_unix; then
    if command -v python3 >/dev/null 2>&1; then
      PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
      PYTHON_CMD="python"
    fi
  fi

  if [[ -z "$PYTHON_CMD" ]]; then
    echo "Automatic installation failed. Please install Python 3.9+ manually and re-run this script." >&2
    exit 1
  fi
fi

if [[ $NO_VENV -eq 0 ]]; then
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

echo "Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel

if [[ -n "$EXTRAS" ]]; then
  echo "Installing package with extras: $EXTRAS"
  # extras must be quoted to avoid shell globbing
  python -m pip install -e ".[$EXTRAS]"
else
  echo "Installing package (editable) without extras"
  python -m pip install -e .
fi

echo "Installation complete."
echo "To activate the virtualenv: source $VENV_DIR/bin/activate"
echo "If you're on Windows (PowerShell), run:"
echo "  python -m venv .venv"
echo "  .\\.venv\\Scripts\\Activate.ps1"
echo "  python -m pip install --upgrade pip setuptools wheel"
echo "  python -m pip install -e .[all]   # optional extras"
