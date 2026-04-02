$ErrorActionPreference = "Stop"

$src = "C:\Users\This Pc\AppData\Local\wsl\{44ff50a3-8557-45a9-ab23-db86607c3515}"
$dst = "E:\wsl\UbuntuBase\{44ff50a3-8557-45a9-ab23-db86607c3515}"

Write-Host "C free GB (before):" ([math]::Round((Get-PSDrive C).Free/1GB,2))

try { wsl --shutdown | Out-Null } catch {}

if (-not (Test-Path $src)) {
  throw "Source BasePath not found: $src"
}
if (Test-Path $dst) {
  throw "Destination already exists: $dst"
}

New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null

Write-Host "Moving BasePath folder to E:..."
Move-Item -Force $src $dst

Write-Host "Creating junction at original path..."
cmd /c "mklink /J `"$src`" `"$dst`""

Write-Host "Done."
Write-Host "C free GB (after):" ([math]::Round((Get-PSDrive C).Free/1GB,2))

