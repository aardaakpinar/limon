<#
.SYNOPSIS
    limon - Windows kolay kurulum beti─şi

.DESCRIPTION
    .venv sanal ortam─▒ olu┼şturur, limon'u (istenen extralarla) kurar ve
    'limon' komutunu %USERPROFILE%\.local\bin alt─▒na kopyalay─▒p PATH'e ekler;
    b├Âylece sanal ortam─▒ etkinle┼ştirmeden her terminalden ├ğal─▒┼ş─▒r.

.PARAMETER Extras
    Kurulacak ekstra sa─şlay─▒c─▒ ba─ş─▒ml─▒l─▒klar─▒: all, claude, openai, gemini.

.PARAMETER VenvDir
    Kullan─▒lacak sanal ortam klas├Âr├╝ (varsay─▒lan: .venv).

.PARAMETER NoVenv
    Belirtilirse sanal ortam olu┼şturmadan mevcut Python ortam─▒na kurar.

.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -Extras claude -VenvDir .venv2
#>

[CmdletBinding()]
param(
    [string]$Extras = "all",
    [string]$VenvDir = ".venv",
    [switch]$NoVenv
)

$ErrorActionPreference = "Stop"

function Write-Info  { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Green }
function Write-Warn2 { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Yellow }
function Write-Err2  { param([string]$Message) Write-Host "HATA: $Message" -ForegroundColor Red }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# --- Python kontrol├╝ ---------------------------------------------------------
$PythonBin = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $PythonBin = $candidate
        break
    }
}

if (-not $PythonBin) {
    Write-Err2 "Python 3.9+ bulunamad─▒. L├╝tfen Python'u kurup PATH'e ekleyin ve tekrar deneyin."
    exit 1
}

# 'py' launcher kullan─▒l─▒yorsa -3 ile Python 3'├╝ zorla
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
if (-not $NoVenv) {
    if (Test-Path $VenvDir) {
        Write-Info "Mevcut sanal ortam kullaniliyor: $VenvDir"
    } else {
        Write-Info "Sanal ortam olusturuluyor: $VenvDir"
        & $PythonBin @PythonArgsPrefix -m venv $VenvDir
    }

    # Activate.ps1 gerekmez (ve script calistirma politikasina takilmaz):
    # dogrudan sanal ortamin python.exe'sini kullaniyoruz.
    $VenvScripts = Join-Path (Resolve-Path $VenvDir).Path "Scripts"
    $VenvPython  = Join-Path $VenvScripts "python.exe"

    if (-not (Test-Path $VenvPython)) {
        Write-Err2 "'$VenvPython' bulunamadi. '$VenvDir' klasorunu silip tekrar deneyin."
        exit 1
    }

    $PythonBin = $VenvPython
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

if ($LASTEXITCODE -ne 0) {
    Write-Err2 "Kurulum basarisiz oldu (pip cikis kodu: $LASTEXITCODE)."
    exit 1
}

# --- 'limon' komutunu sanal ortamin disinda da kullanilabilir yap -----------------
if (-not $NoVenv) {
    $LimonExe = Join-Path $VenvScripts "limon.exe"
    $BinDir   = Join-Path $env:USERPROFILE ".local\bin"

    if (Test-Path $LimonExe) {
        New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
        Copy-Item $LimonExe (Join-Path $BinDir "limon.exe") -Force
        Write-Info "Komut kopyalandi: $(Join-Path $BinDir 'limon.exe')"

        $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $Entries  = @($UserPath -split ";" | Where-Object { $_ })
        if ($Entries -notcontains $BinDir) {
            [Environment]::SetEnvironmentVariable("Path", (($Entries + $BinDir) -join ";"), "User")
            Write-Info "$BinDir kullanici PATH'ine eklendi. Yeni bir terminal acin."
        }
    } else {
        Write-Warn2 "'$LimonExe' bulunamadi; komut PATH'e eklenemedi."
    }
}

Write-Host ""
Write-Info "Kurulum tamamlandi!"
Write-Host "Kullanmaya baslamak icin (yeni bir terminalde):"
Write-Host "  limon config     # saglayici / model / API anahtari ayarla"
Write-Host "  limon            # etkilesimli REPL'i baslat"
