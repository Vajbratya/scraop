# Requires: Windows 10/11, PowerShell as Administrator
# This script installs WSL2, Docker Desktop, and Python 3.10, then prepares the project.

$ErrorActionPreference = "Stop"

function Ensure-Admin {
  $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Please run this script in an elevated PowerShell (Run as Administrator)."
  }
}

function Ensure-Winget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "winget not found. Please install the Microsoft App Installer from Microsoft Store and re-run."
  }
}

function Enable-WSL2 {
  try {
    wsl --set-default-version 2 | Out-Null
  } catch { Write-Host "WSL2 check: $_" }
}

function Install-DockerDesktop {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
  } else {
    Write-Host "Docker is already installed."
  }
}

function Install-Python310 {
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    winget install -e --id Python.Python.3.10 --accept-package-agreements --accept-source-agreements
  } else {
    Write-Host "Python detected: $(python --version)"
  }
}

function Set-ProjectEnv {
  $root = (Resolve-Path "$PSScriptRoot\..\").Path
  $envPath = Join-Path $root ".env"
  if (-not (Test-Path $envPath)) {
    Copy-Item (Join-Path $root ".env.example") $envPath -ErrorAction SilentlyContinue
  }
  Write-Host "Ensure .env has FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD, POSTGRES_* variables set."
}

Ensure-Admin
Ensure-Winget
Enable-WSL2
Install-DockerDesktop
Install-Python310
Set-ProjectEnv

Write-Host "Setup finished. Restart Docker Desktop if it was just installed, then run:"
Write-Host "  docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build"
Write-Host "Frontend: http://localhost:5173  |  Backend: http://localhost:8000  |  Docs: http://localhost:8000/docs"
