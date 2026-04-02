$ErrorActionPreference = "Stop"

$src = "C:\Users\This Pc\AppData\Local\wsl\{44ff50a3-8557-45a9-ab23-db86607c3515}"
$dst = "E:\wsl\UbuntuBase\{44ff50a3-8557-45a9-ab23-db86607c3515}"

try { wsl --shutdown | Out-Null } catch {}

if (-not (Test-Path $dst)) { throw "Destination missing: $dst" }

if (Test-Path $src) {
  Remove-Item -Recurse -Force $src
}

$cmd = "mklink /J `"$src`" `"$dst`""
Write-Host $cmd
cmd /c $cmd

Write-Host "C free GB:" ([math]::Round((Get-PSDrive C).Free/1GB,2))

