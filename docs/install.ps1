##############################################################################
# 🍋 Limon - Windows Installation Script (PowerShell)
# 
# Bu script otomatik olarak:
# - Node.js kontrolü yapıyor
# - Gerekli araçları yükliyor
# - Ollama kurulmasını soruyor
# - Limon'u hazırlıyor
#
# Kullanım: powershell -ExecutionPolicy Bypass -File install.ps1
##############################################################################

# Enable error reporting
$ErrorActionPreference = "Continue"

# Define colors
$Colors = @{
    Red    = [ConsoleColor]::Red
    Green  = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue   = [ConsoleColor]::Blue
    Cyan   = [ConsoleColor]::Cyan
    Gray   = [ConsoleColor]::Gray
}

function Write-Header {
    Write-Host "`n"
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor $Colors.Blue
    Write-Host "🍋 Limon - Windows Installation Script" -ForegroundColor $Colors.Cyan
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor $Colors.Blue
    Write-Host "`n"
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $Colors.Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $Colors.Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $Colors.Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "◆ $Message" -ForegroundColor $Colors.Cyan
}

function Write-Separator {
    Write-Host "────────────────────────────────────────────────────────────" -ForegroundColor $Colors.Blue
}

function Check-NodeJS {
    Write-Host "`n1️⃣  Checking Node.js..." -ForegroundColor $Colors.Blue
    
    try {
        $NodeVersion = node --version
        $NodeMajor = [int]($NodeVersion -replace 'v(\d+)\..*', '$1')
        
        if ($NodeMajor -ge 18) {
            Write-Success "Node.js $NodeVersion found"
            return $true
        } else {
            Write-Error "Node.js 18+ required (found $NodeVersion)"
            Install-NodeJS
            return $true
        }
    }
    catch {
        Write-Warning "Node.js not found"
        Install-NodeJS
        return $true
    }
}

function Install-NodeJS {
    Write-Info "Installing Node.js 18+..."
    Write-Host "`nPlease download and install Node.js from:"
    Write-Host "https://nodejs.org/" -ForegroundColor $Colors.Cyan
    Write-Host "`nChoose the LTS version and follow the installer."
    Write-Host "After installation, please run this script again.`n"
    
    $response = Read-Host "Have you installed Node.js? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Error "Node.js installation required. Exiting."
        exit 1
    }
    
    # Check again
    try {
        $NodeVersion = node --version
        Write-Success "Node.js $NodeVersion installed"
    }
    catch {
        Write-Error "Node.js still not found. Please install manually."
        exit 1
    }
}

function Check-Git {
    Write-Host "`n2️⃣  Checking Git..." -ForegroundColor $Colors.Blue
    
    try {
        $GitVersion = git --version
        Write-Success "$GitVersion found"
        return $true
    }
    catch {
        Write-Warning "Git not found"
        Install-Git
        return $true
    }
}

function Install-Git {
    Write-Info "Installing Git..."
    Write-Host "`nPlease download and install Git from:"
    Write-Host "https://git-scm.com/download/win" -ForegroundColor $Colors.Cyan
    Write-Host "`nFollow the installer with default settings.`n"
    
    $response = Read-Host "Have you installed Git? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Warning "Git is optional but recommended. Continuing..."
        return
    }
    
    try {
        $GitVersion = git --version
        Write-Success "$GitVersion installed"
    }
    catch {
        Write-Warning "Git still not found. You can install it later manually."
    }
}

function Ask-Ollama {
    Write-Host "`n3️⃣  Ollama Installation" -ForegroundColor $Colors.Blue
    Write-Host "`n"
    
    $response = Read-Host "Do you want to install Ollama? (y/N)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Install-Ollama
    } else {
        Write-Info "Skipped Ollama installation"
        Write-Warning "Note: You'll need an API key for Gemini, Claude, or OpenAI"
    }
}

function Install-Ollama {
    Write-Info "Installing Ollama..."
    
    # Check if already installed
    try {
        $OllamaVersion = ollama --version
        Write-Success "$OllamaVersion already installed"
        return
    }
    catch {
        # Not installed, proceed with installation
    }
    
    Write-Info "Downloading Ollama installer..."
    
    try {
        # Download and execute Ollama installer
        $OllamaInstallerUrl = "https://ollama.com/install.ps1"
        $OllamaInstaller = "$env:TEMP\install_ollama.ps1"
        
        # Download the installer
        Invoke-WebRequest -Uri $OllamaInstallerUrl -OutFile $OllamaInstaller -UseBasicParsing
        
        Write-Info "Running Ollama installer..."
        & $OllamaInstaller
        
        # Clean up
        Remove-Item $OllamaInstaller -Force -ErrorAction SilentlyContinue
        
        Write-Success "Ollama installed"
        
        Write-Info "Please restart your computer for Ollama to work properly."
        $restartResponse = Read-Host "Restart now? (y/N)"
        if ($restartResponse -eq 'y' -or $restartResponse -eq 'Y') {
            Restart-Computer -Force
            exit 0
        }
    }
    catch {
        Write-Error "Failed to install Ollama automatically"
        Write-Info "Please download and install manually from:"
        Write-Host "https://ollama.com/" -ForegroundColor $Colors.Cyan
    }
}

function Setup-Limon {
    Write-Host "`n4️⃣  Setting up Limon..." -ForegroundColor $Colors.Blue
    Write-Host "`n"
    
    # Check if package.json exists
    if (-not (Test-Path "package.json")) {
        Write-Error "package.json not found"
        Write-Info "Please run this script from the Limon directory:"
        Write-Host "  cd limon"
        Write-Host "  powershell -ExecutionPolicy Bypass -File install.ps1`n"
        exit 1
    }
    
    Write-Success "Limon directory ready"
}

function Install-Dependencies {
    Write-Host "`n5️⃣  Installing Node.js dependencies..." -ForegroundColor $Colors.Blue
    Write-Host "`n"
    
    if (Test-Path "package.json") {
        Write-Info "Running npm install..."
        npm install --no-save
        Write-Success "Dependencies installed"
    } else {
        Write-Warning "No package.json found, skipping npm install"
    }
}

function Setup-Limon-Config {
    Write-Host "`n6️⃣  Creating Limon configuration..." -ForegroundColor $Colors.Blue
    Write-Host "`n"
    
    $LimonConfigDir = "$env:USERPROFILE\.limon"
    
    if (Test-Path $LimonConfigDir) {
        Write-Info "Limon config directory already exists"
        return
    }
    
    Write-Info "Creating Limon configuration directory..."
    New-Item -ItemType Directory -Path $LimonConfigDir -Force | Out-Null
    
    Write-Success "Config directory created at $LimonConfigDir"
}

function Print-NextSteps {
    Write-Host "`n"
    Write-Separator
    Write-Host "`nNext steps:`n" -ForegroundColor $Colors.Green
    
    Write-Host "1. Run Limon setup:"
    Write-Host "   node index.js --setup" -ForegroundColor $Colors.Cyan
    Write-Host ""
    
    Write-Host "2. Choose your AI provider:"
    Write-Host "   [1] Google Gemini (Free tier available)"
    Write-Host "   [2] Anthropic Claude"
    Write-Host "   [3] OpenAI ChatGPT"
    Write-Host "   [4] Ollama (Local, offline)`n"
    
    try {
        $OllamaCheck = ollama --version
        Write-Host "3. Start Ollama (if not running):"
        Write-Host "   ollama serve`n" -ForegroundColor $Colors.Cyan
    }
    catch {
        # Ollama not installed
    }
    
    Write-Host "4. Start using Limon:"
    Write-Host "   node index.js`n" -ForegroundColor $Colors.Cyan
    
    Write-Host "For more information:"
    Write-Host "   Get-Content README.md"
    Write-Host "   Get-Content QUICKSTART.md`n" -ForegroundColor $Colors.Cyan
    
    Write-Separator
}

# Main installation
function Main {
    Write-Header
    
    Check-NodeJS
    Check-Git
    Ask-Ollama
    Setup-Limon
    Install-Dependencies
    Setup-Limon-Config
    
    Write-Success "Installation complete!"
    Write-Host "`n🍋 Limon is ready to use!`n" -ForegroundColor $Colors.Green
    
    Print-NextSteps
    
    Write-Host "`n"
}

# Run main
Main

exit 0