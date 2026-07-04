<#
.SYNOPSIS
    limon - Windows kolay kurulum betiği

.DESCRIPTION
    .venv sanal ortamı oluşturur ve limon'u (istenen extralarla) kurar.

.PARAMETER Extras
    Kurulacak ekstra sağlayıcı bağımlılıkları: all, claude, openai, gemini.

.PARAMETER VenvDir
    Kullanılacak sanal ortam klasörü (varsayılan: .venv).

.PARAMETER NoVenv
    Belirtilirse sanal ortam oluşturmadan mevcut Python ortamına kurar.

.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -Extras all
.EXAMPLE
    .\install.ps1 -Extras claude -VenvDir .venv2
#>

[CmdletBinding()]
param(
    [string]$Extras = "",
    [string]$VenvDir = ".venv",
    [switch]$NoVenv
)

$ErrorActionPreference = "Stop"

function Write-Info  { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Green }
function Write-Warn2 { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Yellow }
function Write-Err2  { param([string]$Message) Write-Host "HATA: $Message" -ForegroundColor Red }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# --- Python kontrolü ---------------------------------------------------------
$PythonBin = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $PythonBin = $candidate
        break
    }
}

if (-not $PythonBin) {
    Write-Err2 "Python 3.9+ bulunamadı. Lütfen Python'u kurup PATH'e ekleyin ve tekrar deneyin."
    exit 1
}

# 'py' launcher kullanılıyorsa -3 ile Python 3'ü zorla
$PythonArgsPrefix = @()
if ($PythonBin -eq "py") {
    $PythonArgsPrefix = @("-3")
}

$VersionOutput = & $PythonBin @PythonArgsPrefix -c "import sys; print('%d.%d' % sys.version_info[:2])"
Write-Info "Python bulundu: $PythonBin $VersionOutput"

$VersionParts = $VersionOutput.Split(".")
$MajorVersion = [int]$VersionParts[0]
$MinorVersion = [int]$VersionParts[1]

if ($MajorVersion -lt 3 -or ($MajorVersion -eq 3 -and $MinorVersion -lt 9)) {
    Write-Err2 "limon icin Python >= 3.9 gerekiyor, bulunan: $VersionOutput"
    exit 1
}

# --- Sanal ortam --------------------------------------------------------------
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"

if (-not $NoVenv) {
    if (Test-Path $VenvDir) {
        Write-Info "Mevcut sanal ortam kullaniliyor: $VenvDir"
    } else {
        Write-Info "Sanal ortam olusturuluyor: $VenvDir"
        & $PythonBin @PythonArgsPrefix -m venv $VenvDir
    }

    if (-not (Test-Path $ActivateScript)) {
        Write-Err2 "'$ActivateScript' bulunamadi. '$VenvDir' klasorunu silip tekrar deneyin."
        exit 1
    }

    Write-Info "Sanal ortam etkinlestiriliyor..."
    try {
        & $ActivateScript
    } catch {
        Write-Err2 "Sanal ortam etkinlestirilemedi. Script calistirma politikasi engelliyor olabilir."
        Write-Host "Su komutu ayri bir satirda calistirip tekrar deneyin:" -ForegroundColor Yellow
        Write-Host "  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned"
        exit 1
    }

    $PythonBin = "python"
    $PythonArgsPrefix = @()
} else {
    Write-Warn2 "-NoVenv verildi; paketler mevcut Python ortamina kurulacak."
}

# --- pip guncelle --------------------------------------------------------------
Write-Info "pip guncelleniyor..."
& $PythonBin @PythonArgsPrefix -m pip install --upgrade pip | Out-Null

# --- Kurulum ---------------------------------------------------------------
if ($Extras -ne "") {
    Write-Info "limon kuruluyor (extras: $Extras)..."
    & $PythonBin @PythonArgsPrefix -m pip install -e ".[$Extras]"
} else {
    Write-Info "limon kuruluyor (temel bagimliliklar)..."
    & $PythonBin @PythonArgsPrefix -m pip install -e "."
}

Write-Host ""
Write-Info "Kurulum tamamlandi!"
if (-not $NoVenv) {
    Write-Host "Sanal ortami etkinlestirmek icin:"
    Write-Host "  $ActivateScript"
}
Write-Host "Kullanmaya baslamak icin:"
Write-Host "  limon config     # saglayici / model / API anahtari ayarla"
Write-Host "  limon            # etkilesimli REPL'i baslat"
