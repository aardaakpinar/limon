<#
Windows installer for the project.
Tries to ensure Python 3 is installed (winget/choco), creates a virtualenv (.venv) by default,
upgrades pip/setuptools/wheel and installs the package in editable mode. Supports extras.

Usage examples:
  powershell -ExecutionPolicy Bypass -File .\install.ps1
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Extras all
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -NoVenv
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Force
#>

param(
  [switch]$Force,
  [string]$Extras = "",
  [switch]$NoVenv
)

function Has-Python {
  try {
    & python --version > $null 2>&1
    return $true
  } catch {
    return $false
  }
}

function Install-Python-Windows {
  $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    Write-Warning "Not running as Administrator. System-wide install may fail; run PowerShell as Administrator if possible."
  }

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Output "Installing Python via winget..."
    try {
      Start-Process -FilePath winget -ArgumentList 'install','--id','Python.Python.3','-e','--accept-source-agreements','--accept-package-agreements' -NoNewWindow -Wait
      return $true
    } catch {
      Write-Warning "winget install failed."
    }
  }

  if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Output "Installing Python via Chocolatey..."
    try {
      Start-Process -FilePath choco -ArgumentList 'install','python','-y' -NoNewWindow -Wait
      return $true
    } catch {
      Write-Warning "choco install failed."
    }
  }

  Write-Warning "Automatic installers not available or installation failed. Opening python.org download page..."
  Start-Process "https://www.python.org/downloads/windows/"
  return $false
}

# Ensure Python is present (or install it)
if (Has-Python -and -not $Force) {
  $v = (& python --version 2>&1).Trim()
  Write-Output "Python already installed: $v"
} else {
  if (-not (Has-Python)) {
    Write-Output "Python not found — attempting automatic install..."
    if (-not (Install-Python-Windows)) {
      Write-Error "Could not install Python automatically. Please install Python 3.9+ manually and re-run this script."
      exit 1
    }
    Start-Sleep -Seconds 2
    if (-not (Has-Python)) {
      Write-Error "Python still not available after installer. Aborting."
      exit 1
    }
  }
}

$ScriptDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent

function Get-Python-For-Install {
  if ($NoVenv) {
    return (Get-Command python -ErrorAction Stop).Source
  }
  $venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    return $venvPython
  }
  return (Get-Command python -ErrorAction Stop).Source
}

if (-not $NoVenv) {
  $venvPath = Join-Path $ScriptDir ".venv"
  if (-not (Test-Path $venvPath)) {
    Write-Output "Creating virtual environment at $venvPath..."
    & (Get-Command python -ErrorAction Stop).Source -m venv $venvPath
  }
}

$pythonExe = Get-Python-For-Install

Write-Output "Using Python: $pythonExe"

Write-Output "Upgrading pip, setuptools, wheel..."
& $pythonExe -m pip install --upgrade pip setuptools wheel

if ($Extras -ne "") {
  Write-Output "Installing package with extras: $Extras"
  & $pythonExe -m pip install -e ".[$Extras]"
} else {
  Write-Output "Installing package (editable) without extras"
  & $pythonExe -m pip install -e .
}

Write-Output "Installation complete."
if (-not $NoVenv) {
  Write-Output "To activate the virtualenv in PowerShell: .\ .venv\Scripts\Activate.ps1"
} else {
  Write-Output "Using system Python; no virtual environment was created."
}
