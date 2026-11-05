param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'Port 8000 is already in use. Check http://127.0.0.1:8000 before starting another instance.'
    exit 0
}
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
uv sync --project backend --frozen
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
if (-not $SkipBuild) {
    Push-Location web
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Web dependency installation failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
    } finally { Pop-Location }
}
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$backendRoot = Join-Path $projectRoot 'backend'
$dataRoot = Join-Path $projectRoot 'data'
New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dataRoot 'api.out.log') -RedirectStandardError (Join-Path $dataRoot 'api.err.log')
$apiHealthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
        if ($health.status -eq 'ok') { $apiHealthy = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 500
}
if (-not $apiHealthy) { throw 'API did not become healthy. Inspect data/api.err.log before starting the worker.' }
$workerProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','app.jobs') -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dataRoot 'worker.out.log') -RedirectStandardError (Join-Path $dataRoot 'worker.err.log')
Start-Sleep -Milliseconds 500
$ownedProcesses = @()
foreach ($rootPid in @($apiProcess.Id, $workerProcess.Id)) {
    $rootProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$rootPid"
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$rootPid")
    foreach ($owned in @($rootProcess) + $children) {
        if ($owned -and $owned.CommandLine -match 'app\.main:app|app\.jobs') {
            $ownedProcesses += @{ id=$owned.ProcessId; created=$owned.CreationDate.ToUniversalTime().ToString('o') }
        }
    }
}
@{ api=$apiProcess.Id; worker=$workerProcess.Id; started=(Get-Date).ToString('o'); processes=$ownedProcesses } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dataRoot 'processes.json')
Write-Host 'App starting: http://127.0.0.1:8000'
Write-Host 'API reference: http://127.0.0.1:8000/docs'
Write-Host 'Logs are in data/. Stop with scripts/stop.ps1.'
