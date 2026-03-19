#!/bin/bash

##############################################################################
# 🍋 Limon - Linux/macOS Installation Script
# 
# Bu script otomatik olarak:
# - Node.js kontrolü yapıyor
# - Gerekli araçları yükliyor
# - Ollama kurulmasını soruyor
# - Limon'u hazırlıyor
#
# Kullanım: bash install.sh
##############################################################################

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}🍋 Limon - Installation Script${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}◆${NC} $1"
}

separator() {
    echo -e "${BLUE}────────────────────────────────────────────────────────────${NC}"
}

# Main installation
main() {
    print_header
    
    # Detect OS
    detect_os
    
    # Check Node.js
    echo -e "\n${BLUE}1️⃣  Checking Node.js...${NC}"
    check_nodejs
    
    # Check Git
    echo -e "\n${BLUE}2️⃣  Checking Git...${NC}"
    check_git
    
    # Ask about Ollama
    echo -e "\n${BLUE}3️⃣  Ollama Installation${NC}"
    ask_ollama
    
    # Clone or copy repository
    echo -e "\n${BLUE}4️⃣  Setting up Limon...${NC}"
    setup_limon
    
    # Install dependencies
    echo -e "\n${BLUE}5️⃣  Installing Node.js dependencies...${NC}"
    install_dependencies
    
    # Final setup
    echo -e "\n${BLUE}6️⃣  Running Limon setup...${NC}"
    setup_limon_config
    
    print_success "Installation complete!"
    echo -e "\n${GREEN}🍋 Limon is ready to use!${NC}\n"
    print_next_steps
}

detect_os() {
    case "$(uname -s)" in
        Linux*)
            OS="Linux"
            PACKAGE_MANAGER="apt"
            ;;
        Darwin*)
            OS="macOS"
            PACKAGE_MANAGER="brew"
            ;;
        *)
            print_error "Unsupported operating system"
            exit 1
            ;;
    esac
    print_success "Detected OS: $OS"
}

check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        NODE_MAJOR=$(echo $NODE_VERSION | cut -d'v' -f2 | cut -d'.' -f1)
        
        if [ "$NODE_MAJOR" -ge 18 ]; then
            print_success "Node.js $NODE_VERSION found"
        else
            print_error "Node.js 18+ required (found $NODE_VERSION)"
            install_nodejs
        fi
    else
        print_warning "Node.js not found"
        install_nodejs
    fi
}

install_nodejs() {
    echo ""
    print_info "Installing Node.js 18+..."
    
    if [ "$OS" = "Linux" ]; then
        sudo apt-get update
        sudo apt-get install -y nodejs npm
    elif [ "$OS" = "macOS" ]; then
        if ! command -v brew &> /dev/null; then
            print_info "Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install node
    fi
    
    NODE_VERSION=$(node --version)
    print_success "Node.js $NODE_VERSION installed"
}

check_git() {
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version)
        print_success "$GIT_VERSION found"
    else
        print_warning "Git not found"
        install_git
    fi
}

install_git() {
    echo ""
    print_info "Installing Git..."
    
    if [ "$OS" = "Linux" ]; then
        sudo apt-get install -y git
    elif [ "$OS" = "macOS" ]; then
        brew install git
    fi
    
    print_success "Git installed"
}

ask_ollama() {
    echo ""
    read -p "$(echo -e ${YELLOW})Do you want to install Ollama? (y/N)$(echo -e ${NC}) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_ollama
    else
        print_info "Skipped Ollama installation"
        print_warning "Note: You'll need an API key for Gemini, Claude, or OpenAI"
    fi
}

install_ollama() {
    echo ""
    print_info "Installing Ollama..."
    
    if command -v ollama &> /dev/null; then
        OLLAMA_VERSION=$(ollama --version)
        print_success "$OLLAMA_VERSION already installed"
        return
    fi
    
    # Download and run Ollama installer
    if [ "$OS" = "Linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [ "$OS" = "macOS" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    print_success "Ollama installed"
    echo ""
    print_info "Starting Ollama service..."
    
    if [ "$OS" = "Linux" ]; then
        sudo systemctl start ollama
        sudo systemctl enable ollama
    elif [ "$OS" = "macOS" ]; then
        brew services start ollama
    fi
    
    print_success "Ollama service started"
}

setup_limon() {
    echo ""
    
    # Check if we're in limon directory
    if [ ! -f "package.json" ]; then
        print_info "Creating Limon directory..."
        
        if [ -d "limon" ]; then
            cd limon
        else
            print_error "Please run this script from the Limon directory"
            print_info "Or clone it first:"
            echo "  git clone <limon-repo>"
            echo "  cd limon"
            echo "  bash install.sh"
            exit 1
        fi
    fi
    
    print_success "Limon directory ready"
}

install_dependencies() {
    echo ""
    print_info "Installing Node.js dependencies..."
    
    if [ -f "package.json" ]; then
        npm install --no-save
        print_success "Dependencies installed"
    else
        print_warning "No package.json found, skipping npm install"
    fi
}

setup_limon_config() {
    echo ""
    
    # Check if config exists
    if [ -d "$HOME/.limon" ]; then
        print_info "Limon config directory already exists"
        return
    fi
    
    print_info "Creating Limon configuration directory..."
    mkdir -p "$HOME/.limon"
    
    print_success "Config directory created at $HOME/.limon"
}

print_next_steps() {
    separator
    echo -e "\n${GREEN}Next steps:${NC}\n"
    
    echo "1. Run Limon setup:"
    echo -e "   ${CYAN}node index.js --setup${NC}\n"
    
    echo "2. Choose your AI provider:"
    echo "   [1] Google Gemini (Free tier available)"
    echo "   [2] Anthropic Claude"
    echo "   [3] OpenAI ChatGPT"
    echo -e "   [4] Ollama (Local, offline)\n"
    
    if command -v ollama &> /dev/null; then
        echo "3. Start Ollama (if not running):"
        echo -e "   ${CYAN}ollama serve${NC}\n"
    fi
    
    echo "4. Start using Limon:"
    echo -e "   ${CYAN}node index.js${NC}\n"
    
    echo "For more information:"
    echo -e "   ${CYAN}cat README.md${NC}"
    echo -e "   ${CYAN}cat QUICKSTART.md${NC}\n"
    
    separator
}

# Run main
main

exit 0