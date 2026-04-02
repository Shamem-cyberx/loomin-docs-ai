$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Get-ChildItem -Path $root -Recurse -Filter *.sh -File | ForEach-Object {
    $c = Get-Content -Raw -LiteralPath $_.FullName
    $c = $c -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($_.FullName, $c, [System.Text.UTF8Encoding]::new($false))
}
Write-Host "Normalized *.sh under $root"
