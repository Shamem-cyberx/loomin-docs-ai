#Requires -Version 5.1
<#
  From Windows (PowerShell), run the full WSL test pipeline.
  Usage (Admin optional — only needed if you repair WSL disk first):
    cd E:\loomin-docs
    .\scripts\Run-RagTests.ps1

  Override WSL path if the repo is not on E::
    .\scripts\Run-RagTests.ps1 -WslRepoPath "/mnt/d/work/loomin-docs"
#>
param(
    [string]$WslRepoPath = "/mnt/e/loomin-docs"
)

$ErrorActionPreference = "Stop"

Write-Host "=== WSL smoke test ===" -ForegroundColor Cyan
$wslTest = & wsl.exe -e bash -lc "echo OK" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "WSL failed to start:" -ForegroundColor Red
    Write-Host $wslTest
    Write-Host ""
    Write-Host "If the error mentions ext4.vhdx / FILE_NOT_FOUND, run (same folder):" -ForegroundColor Yellow
    Write-Host "  .\scripts\Recover-WslDisk.ps1" -ForegroundColor Yellow
    Write-Host "Or restore Ubuntu from Windows Store / reinstall WSL after freeing disk on C:." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Running wsl_run_all.sh (LOOMIN_ROOT=$WslRepoPath) ===" -ForegroundColor Cyan
Write-Host "Tip: for faster reruns after images exist: wsl -e bash -lc `"export LOOMIN_ROOT='$WslRepoPath' SKIP_BUILD=1; bash $WslRepoPath/scripts/wsl_run_all.sh`"" -ForegroundColor DarkGray
& wsl.exe -e bash -lc "export LOOMIN_ROOT='$WslRepoPath'; bash `"$WslRepoPath/scripts/wsl_run_all.sh`""
exit $LASTEXITCODE
