#Requires -Version 5.1

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
        $targets += [PSCustomObject]@{
            Name   = $d.Name
            Vhdx   = $v
            Exists = $false
        }
    }
}

if ($targets.Count -eq 0) {
    Write-Host "All distros already have ext4.vhdx." -ForegroundColor Green
    exit 0
}

Write-Host "`n=== Missing ext4.vhdx ===" -ForegroundColor Yellow
$targets | Format-Table -AutoSize

$candidates = @()

if ($SourceVhdx -ne "") {
    if (Test-Path $SourceVhdx) {
        $candidates += (Resolve-Path $SourceVhdx).Path
    }
} else {
    foreach ($letter in @('E','D','F','G','C')) {
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

Write-Host "`n=== Candidate ext4.vhdx files ===" -ForegroundColor Cyan

if ($candidates.Count -eq 0) {
    Write-Host "No VHDX found. Provide manually using -SourceVhdx" -ForegroundColor Red
    exit 2
}

$candidates | ForEach-Object { Write-Host "  $_" }

if ($targets.Count -ne 1) {
    Write-Host "`nMultiple or zero distros missing disk. Fix manually." -ForegroundColor Yellow
    exit 3
}

$dest = $targets[0].Vhdx
$destDir = Split-Path $dest -Parent
$pick = $candidates[0]

if ($candidates.Count -gt 1 -and $SourceVhdx -eq "") {
    Write-Host "`nMultiple candidates found. Using first." -ForegroundColor Yellow
}

Write-Host "`nCopying:"
Write-Host "FROM: $pick"
Write-Host "TO  : $dest" -ForegroundColor Green

if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

Copy-Item -LiteralPath $pick -Destination $dest -Force

Write-Host "`nDone. Run: wsl" -ForegroundColor Green