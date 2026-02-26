param(
  [int]$Minutes = 0
)

$ErrorActionPreference = "Stop"

# Ensure imports work
$env:PYTHONPATH = "."

Write-Host "Starting simulator + aggregator (Minutes=$Minutes)."
Write-Host "Two new PowerShell windows will open."

# Start simulator in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:PYTHONPATH='.'; python -m services.simulator"

# Start aggregator in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:PYTHONPATH='.'; python -m services.aggregator"

Write-Host "Done."
Write-Host "Stop each with Ctrl+C in its window."