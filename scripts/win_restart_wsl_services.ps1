$ErrorActionPreference = "Continue"

Write-Host "Stopping WSL/VM services (if present)..."
$names = @("LxssManager", "WslService", "vmcompute", "hns")
foreach ($n in $names) {
  $svc = Get-Service -Name $n -ErrorAction SilentlyContinue
  if ($svc) {
    Write-Host " - " $n ":" $svc.Status
    if ($svc.Status -eq "Running") {
      try { Stop-Service -Name $n -Force -ErrorAction Stop } catch { Write-Host "   stop failed:" $_.Exception.Message }
    }
  }
}

Write-Host "Starting required services..."
foreach ($n in @("hns","vmcompute","WslService","LxssManager")) {
  $svc = Get-Service -Name $n -ErrorAction SilentlyContinue
  if ($svc) {
    try { Start-Service -Name $n -ErrorAction Stop } catch { }
    $svc = Get-Service -Name $n -ErrorAction SilentlyContinue
    Write-Host " - " $n ":" ($svc.Status)
  }
}

Write-Host "Done. Try: wsl --shutdown; wsl"

