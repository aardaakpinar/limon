<#
.SYNOPSIS
    limon - tek komutla kurulum (Windows). git gerekmez.

.EXAMPLE
    irm https://aardaakpinar.github.io/limon/install.ps1 | iex
.EXAMPLE
    $env:LIMON_EXTRAS = "claude"; irm https://aardaakpinar.github.io/limon/install.ps1 | iex

.NOTES
    Kodlari %USERPROFILE%\.limon\src altina indirir, sanal ortami %USERPROFILE%\.limon\venv
    icinde kurar. Ayni komutu tekrar calistirmak gunceller.
    Surum: varsayilan olarak GitHub'daki SON SURUM etiketi kurulur (yayin yoksa main dali).
    Ortam degiskenleri: LIMON_EXTRAS (varsayilan all), LIMON_HOME,
                        LIMON_REF (etiket/dal, or. v0.2.0 veya main)
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Windows PowerShell 5.1'de indirmeyi cok yavaslatir
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$Repo   = "aardaakpinar/limon"
$Ref    = $env:LIMON_REF
$Extras = if ($env:LIMON_EXTRAS) { $env:LIMON_EXTRAS } else { "all" }
$Home2  = if ($env:LIMON_HOME)   { $env:LIMON_HOME }   else { Join-Path $env:USERPROFILE ".limon" }
if (-not $Ref) {
    try {
        $Ref = (Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -TimeoutSec 10).tag_name
    } catch { $Ref = $null }
    if (-not $Ref) { $Ref = "main" }
}
$Url    = "https://github.com/$Repo/archive/$Ref.zip"

$Tmp = Join-Path ([IO.Path]::GetTempPath()) ("limon-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

try {
    Write-Host "==> limon indiriliyor ($Repo@$Ref)..." -ForegroundColor Green
    $Zip = Join-Path $Tmp "limon.zip"
    Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing
    Expand-Archive -Path $Zip -DestinationPath (Join-Path $Tmp "out") -Force

    $Extracted = Get-ChildItem (Join-Path $Tmp "out") -Directory | Select-Object -First 1
    if (-not $Extracted -or -not (Test-Path (Join-Path $Extracted.FullName "pyproject.toml"))) {
        throw "Indirilen arsiv beklenen yapida degil."
    }

    New-Item -ItemType Directory -Force -Path $Home2 | Out-Null
    $Src = Join-Path $Home2 "src"
    if (Test-Path $Src) { Remove-Item $Src -Recurse -Force }
    Move-Item $Extracted.FullName $Src
    Write-Host "==> Kodlar yerlestirildi: $Src" -ForegroundColor Green

    # Asil kurulumu depodaki install.ps1 yapar. Betik dosyasi calistirma politikasina
    # takilmasin diye ayri bir powershell sureci ve -ExecutionPolicy Bypass kullanilir.
    $Venv = Join-Path $Home2 "venv"
    $Exe = if (Get-Command powershell.exe -ErrorAction SilentlyContinue) { "powershell.exe" } else { "pwsh" }
    & $Exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Src "install.ps1") -Extras $Extras -VenvDir $Venv
    if ($LASTEXITCODE -ne 0) { throw "Kurulum basarisiz oldu (cikis kodu: $LASTEXITCODE)." }

    # PATH degisikligi bu pencerede de gecerli olsun (iex ayni oturumda calisir)
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    if (Get-Command limon -ErrorAction SilentlyContinue) {
        Write-Host "==> 'limon' komutu bu pencerede hazir." -ForegroundColor Green
    }
}
catch {
    Write-Host "HATA: $_" -ForegroundColor Red
}
finally {
    Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
}
