#Requires -Version 5.1
<#
  When WSL says ERROR_FILE_NOT_FOUND for ext4.vhdx, this script:
  1) Lists each distro's expected BasePath from the registry
  2) Searches fixed drives (E:, D:, ...) for ext4.vhdx
  3) If exactly one candidate is found (or you pass -SourceVhdx), copies it into the missing BasePath

  Run in PowerShell (Admin recommended if copy fails with Access Denied):
    cd E:\loomin-docs
    .\scripts\Recover-WslDisk.ps1
    .\scripts\Recover-WslDisk.ps1 -SourceVhdx "E:\wsl\UbuntuBase\...\ext4.vhdx"
#>
param(
    [string]$SourceVhdx = ""
)

$ErrorActionPreference = "Continue"

function Get-LxssDistros {
    $root = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss"
    if (-not (Test-Path $root)) { return @() }
    Get-ChildItem $root | ForEach-Object {
        $p = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($p.BasePath -and $p.DistributionName) {
            [PSCustomObject]@{
                Name     = $p.DistributionName
                BasePath = $p.BasePath.TrimEnd('\')
            }
        }
    }
}

Write-Host "=== Registered WSL distros (BasePath) ===" -ForegroundColor Cyan
$distros = @(Get-LxssDistros)
if ($distros.Count -eq 0) {
    Write-Host "No HKCU Lxss entries found." -ForegroundColor Yellow
} else {
    $distros | Format-Table -AutoSize
}

$targets = @()
foreach ($d in $distros) {
    $v = Join-Path $d.BasePath "ext4.vhdx"
    if (-not (Test-Path $v)) {
        $targets += [PSCustomObject]@{ Name = $d.Name; Vhdx = $v; Exists = $false }
    }
}

if ($targets.Count -eq 0) {
    Write-Host "All known distros already have ext4.vhdx on disk (or no distros)." -ForegroundColor Green
    exit 0
}

Write-Host "`n=== Missing ext4.vhdx ===" -ForegroundColor Yellow
$targets | Format-Table -AutoSize

$candidates = @()
if ($SourceVhdx) {
    if (Test-Path $SourceVhdx) { $candidates += (Resolve-Path $SourceVhdx).Path }
} else {
    foreach ($letter in @('E', 'D', 'F', 'G')) {
        $drv = "${letter}:\"
        if (-not (Test-Path $drv)) { continue }
        try {
            Get-ChildItem -Path $drv -Filter "ext4.vhdx" -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.Length -gt 1MB } |
                ForEach-Object { $candidates += $_.FullName }
        } catch {}
    }
    $candidates = $candidates | Select-Object -Unique
}

Write-Host "`n=== Candidate ext4.vhdx files (larger than 1MB) ===" -ForegroundColor Cyan
if ($candidates.Count -eq 0) {
    Write-Host "None found. Put your backup ext4.vhdx somewhere (e.g. E:\backup\ext4.vhdx) and run:" -ForegroundColor Red
    Write-Host '  .\scripts\Recover-WslDisk.ps1 -SourceVhdx "E:\path\to\ext4.vhdx"' -ForegroundColor Yellow
    exit 2
}
$candidates | ForEach-Object { Write-Host "  $_" }

if ($targets.Count -ne 1) {
    Write-Host "`nMultiple or zero missing distros — copy manually to the BasePath shown above." -ForegroundColor Yellow
    exit 3
}

$destDir = Split-Path $targets[0].Vhdx -Parent
$pick = $candidates[0]
if ($candidates.Count -gt 1 -and -not $SourceVhdx) {
    Write-Host "`nMultiple candidates; using first. Specify -SourceVhdx to choose." -ForegroundColor Yellow
}
Write-Host "`nCopying:`n  FROM $pick`n  TO  $($targets[0].Vhdx)" -ForegroundColor Green

if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}
Copy-Item -LiteralPath $pick -Destination $targets[0].Vhdx -Force
Write-Host "Done. Run: wsl" -ForegroundColor Green
