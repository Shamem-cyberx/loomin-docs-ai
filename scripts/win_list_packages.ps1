$ErrorActionPreference = "Stop"
$local = [Environment]::GetFolderPath("LocalApplicationData")
$pkg = Join-Path $local "Packages"
Write-Host "Packages:" $pkg
Get-ChildItem -Path $pkg -Directory -ErrorAction SilentlyContinue |
  Select-Object -First 40 Name |
  ForEach-Object { Write-Host $_.Name }

