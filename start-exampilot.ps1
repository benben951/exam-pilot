$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 8766
$Url = "http://127.0.0.1:$Port/"

Set-Location $ProjectRoot

$EnvFile = Join-Path $ProjectRoot ".env.local"
if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $name, $value = $line.Split("=", 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim().Trim('"'), "Process")
  }
}

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique

if (-not $existing) {
  Start-Process -FilePath "python" `
    -ArgumentList "run_server.py --port $Port" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

  Start-Sleep -Seconds 1
}

Start-Process $Url

Write-Host "ExamPilot is running at $Url"
Write-Host "Close this window whenever you like. The background server may keep running."
