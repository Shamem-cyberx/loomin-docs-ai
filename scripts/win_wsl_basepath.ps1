$ErrorActionPreference = "Stop"

$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss"
if (-not (Test-Path $key)) {
  Write-Host "No Lxss registry key found."
  exit 0
}

Get-ChildItem $key | ForEach-Object {
  $p = Get-ItemProperty $_.PsPath
  [pscustomobject]@{
    DistributionName = $p.DistributionName
    BasePath         = $p.BasePath
    Guid             = $_.PSChildName
  }
} | Format-Table -Auto

