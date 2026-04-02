$ErrorActionPreference = "Stop"

$local = [Environment]::GetFolderPath("LocalApplicationData")
$user = [Environment]::GetFolderPath("UserProfile")

Write-Host "LOCALAPPDATA =" $local
Write-Host "USERPROFILE =" $user
Write-Host "C: FreeGB =" ([math]::Round((Get-PSDrive C).Free / 1GB, 2))

$roots = @(
  (Join-Path $local "Docker\\wsl\\data\\ext4.vhdx"),
  (Join-Path $local "Docker Desktop\\wsl\\data\\ext4.vhdx"),
  (Join-Path $local "lxss\\ext4.vhdx")
)

Write-Host "`n== Common Docker VHDX paths =="
foreach ($p in $roots) {
  if (Test-Path $p) {
    $i = Get-Item $p
    [pscustomobject]@{
      Path   = $i.FullName
      SizeGB = [math]::Round($i.Length / 1GB, 2)
      LastWrite = $i.LastWriteTime
    }
  }
}

Write-Host "`n== Top ext4.vhdx under LocalAppData\\Packages =="
$pkg = Join-Path $local "Packages"
if (Test-Path $pkg) {
  Write-Host "Packages dir exists:" $pkg
  # Direct check: Ubuntu distro VHDX is usually here
  $ubuntuDirs = Get-ChildItem -Path $pkg -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "CanonicalGroupLimited.Ubuntu*" -or $_.Name -like "*Ubuntu*" } |
    Select-Object -First 20
  Write-Host "Ubuntu-like package dirs found:" ($ubuntuDirs.Count)
  $ubuntuDirs | ForEach-Object { Write-Host " - " $_.Name }

  foreach ($d in $ubuntuDirs) {
    $ls = Join-Path $d.FullName "LocalState"
    if (Test-Path $ls) {
      Get-ChildItem -Path $ls -Filter "*.vhdx" -ErrorAction SilentlyContinue | ForEach-Object {
        [pscustomobject]@{ Path=$_.FullName; SizeGB=[math]::Round($_.Length/1GB,2); LastWrite=$_.LastWriteTime }
      }
    }
  }

  # Direct check: docker-desktop-data distro VHDX
  $dockerDirs = Get-ChildItem -Path $pkg -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "*docker-desktop*" -or $_.Name -like "*DockerDesktop*" } |
    Select-Object -First 40
  Write-Host "DockerDesktop-like package dirs found:" ($dockerDirs.Count)
  $dockerDirs | ForEach-Object { Write-Host " - " $_.Name }

  foreach ($d in $dockerDirs) {
    $ls = Join-Path $d.FullName "LocalState"
    if (Test-Path $ls) {
      Get-ChildItem -Path $ls -Filter "*.vhdx" -ErrorAction SilentlyContinue | ForEach-Object {
        [pscustomobject]@{ Path=$_.FullName; SizeGB=[math]::Round($_.Length/1GB,2); LastWrite=$_.LastWriteTime }
      }
    }
  }
}

Write-Host "`n== WSL distros =="
try { wsl -l -v } catch { Write-Host $_.Exception.Message }

