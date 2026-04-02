# Minimal Docker config (no credential helper) for builds when WSL/docker fails with
# "error getting credentials". Run from Windows PowerShell in the repo root:
#   .\scripts\compose-wsl.ps1 build backend frontend collab
#   .\scripts\compose-wsl.ps1 up -d

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:DOCKER_CONFIG = Join-Path $Root "scripts\wsl-docker-config"
Set-Location $Root
& docker compose @args
