param(
  [int]$Minutes = 10,
  [float]$Speed = 60.0
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "."

# Check Redis
$ping = docker exec redis redis-cli ping 2>$null
if ($ping -ne "PONG") {
    Write-Error "Redis is not running. Start it first: docker run -d -p 6379:6379 --name redis redis"
    exit 1
}

Write-Host "Starting aggregator + replay (Minutes=$Minutes, Speed=$Speed)."

Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd `"$PWD`"; `$env:PYTHONPATH='.'; python -m services.aggregator --minutes $Minutes"

# Small delay so aggregator is ready before replay starts
Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd `"$PWD`"; `$env:PYTHONPATH='.'; python -m services.replay --path 'taxi_data.parquet' --speed $Speed --minutes $Minutes"

Write-Host "Done. Both will stop after $Minutes minute(s)."