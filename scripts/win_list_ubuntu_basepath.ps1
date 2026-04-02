$ErrorActionPreference = "Stop"

$base = "C:\Users\This Pc\AppData\Local\wsl\{44ff50a3-8557-45a9-ab23-db86607c3515}"
Write-Host "BasePath =" $base
if (-not (Test-Path $base)) {
  Write-Host "BasePath not found."
  exit 1
}

Get-ChildItem -Force $base | Select-Object Name, @{n="SizeGB";e={[math]::Round($_.Length/1GB,2)}}, Length, LastWriteTime | Format-Table -Auto

