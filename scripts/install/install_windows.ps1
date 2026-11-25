# FLOKTRON · automatic runs on Windows (Task Scheduler).
# Right-click → "Run with PowerShell".  Switch off:  powershell -File install_windows.ps1 off
$root = Resolve-Path "$PSScriptRoot\..\.."
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { Write-Host "Python not found — install it from python.org (tick 'Add to PATH')"; Read-Host; exit 1 }
& $py -c "import openpyxl, yaml, tzdata" 2>$null; if ($LASTEXITCODE -ne 0) { & $py -m pip install --user -q openpyxl pyyaml tzdata }
foreach ($n in "morning","deadline","evening","news","summary","collect","content","gaps","registry","backup","supply","supply_week") { schtasks /Delete /F /TN "FLOKTRON\$n" 2>$null | Out-Null }
if ($args[0] -eq "off") { Write-Host "FLOKTRON automatic runs OFF"; Read-Host; exit 0 }
& $py "$root\scripts\install\schedule.py" windows "$root" "$py" | ForEach-Object { cmd /c $_ }
Write-Host "FLOKTRON automatic runs ON. Log: $root\data\run.log  ·  The computer must stay on."; Read-Host
