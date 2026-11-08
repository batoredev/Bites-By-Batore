param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$backendRoot = Join-Path $projectRoot 'backend'
$dataRoot = Join-Path $projectRoot 'data'
$apiModulePattern = '(?:^|\s)-m\s+["'']?uvicorn["'']?\s+["'']?app\.main:app["'']?(?=\s|$)'
$workerModulePattern = '(?:^|\s)-m\s+["'']?app\.jobs["'']?(?=\s|$)'

function Test-LoopbackPort {
    # Get-NetTCPConnection can miss a working listener on this machine.
    $client = New-Object System.Net.Sockets.TcpClient
    $pending = $null
    try {
        $pending = $client.BeginConnect([System.Net.IPAddress]::Loopback, 8000, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($pending)
        return $true
    } catch { return $false }
    finally {
        if ($pending) { $pending.AsyncWaitHandle.Close() }
        $client.Close()
    }
}

function Get-WorkspaceProcesses {
    $all = @(Get-CimInstance Win32_Process)
    $state = [pscustomobject]@{
        all = $all
        api = @($all | Where-Object { $_.ExecutablePath -ieq $pythonExe -and $_.CommandLine -match $apiModulePattern })
        worker = @($all | Where-Object { $_.ExecutablePath -ieq $pythonExe -and $_.CommandLine -match $workerModulePattern })
    }
    if ($state.api.Count -gt 1 -or $state.worker.Count -gt 1) {
        throw 'Multiple API or worker processes already exist for this workspace. Inspect them before restarting; no process was stopped.'
    }
    return $state
}

function Assert-ProcessRunning($Process, [string]$Name) {
    $Process.Refresh()
    if ($Process.HasExited) {
        throw "$Name process exited (code $($Process.ExitCode)). Inspect data/ logs before restarting."
    }
}

function Wait-ApiHealthy($Process) {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Assert-ProcessRunning $Process 'API'
        $healthy = $false
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
            $healthy = $health.status -eq 'ok'
        } catch { }
        # An old listener must not make an exited new process appear healthy.
        Assert-ProcessRunning $Process 'API'
        if ($healthy) { return }
        Start-Sleep -Milliseconds 500
    }
    throw 'API did not become healthy. Inspect data/api.err.log before starting the worker.'
}

function Write-ProcessRecord($State, [int]$ApiId, [int]$WorkerId) {
    $ownedProcesses = @()
    $seen = @{}
    foreach ($rootProcess in (@($State.api) + @($State.worker))) {
        $children = @($State.all | Where-Object { $_.ParentProcessId -eq $rootProcess.ProcessId })
        foreach ($owned in (@($rootProcess) + $children)) {
            if (-not $seen.ContainsKey($owned.ProcessId) -and ($owned.CommandLine -match $apiModulePattern -or $owned.CommandLine -match $workerModulePattern)) {
                $ownedProcesses += @{ id=$owned.ProcessId; created=$owned.CreationDate.ToUniversalTime().ToString('o') }
                $seen[$owned.ProcessId] = $true
            }
        }
    }
    New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
    @{ api=$ApiId; worker=$WorkerId; started=(Get-Date).ToString('o'); processes=$ownedProcesses } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dataRoot 'processes.json')
}

# Serialize dependency/build work, both process launches and ownership recording.
$hasher = [System.Security.Cryptography.SHA256]::Create()
try {
    $workspaceKey = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\').ToUpperInvariant()
    $workspaceHash = [System.BitConverter]::ToString($hasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($workspaceKey))).Replace('-', '')
} finally { $hasher.Dispose() }
$startMutex = New-Object System.Threading.Mutex($false, "Global\Batore.Start.$workspaceHash")
$ownsMutex = $false
try {
    try { $ownsMutex = $startMutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $ownsMutex = $true }
    if (-not $ownsMutex) {
        Write-Host 'Startup is already in progress for this workspace. Wait for that launcher to finish.'
        return
    }
    Set-Location -LiteralPath $projectRoot
    $state = Get-WorkspaceProcesses
    if ($state.api.Count -eq 0) {
        if (Test-LoopbackPort) {
            Write-Host 'Port 8000 is already in use by another process. No API or worker was started.'
            return
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
        # Recheck after potentially long installs/builds, including older launchers.
        $state = Get-WorkspaceProcesses
        if ($state.api.Count -eq 0) {
            if (Test-LoopbackPort) { throw 'Port 8000 became occupied during setup. No API was started.' }
            New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
            $apiProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dataRoot 'api.out.log') -RedirectStandardError (Join-Path $dataRoot 'api.err.log')
            Start-Sleep -Milliseconds 500
            Assert-ProcessRunning $apiProcess 'API'
        }
    }
    if ($state.api.Count -eq 1) {
        if ($state.api[0].CommandLine -notmatch '(?:^|\s)--port(?:\s+|=)["'']?8000["'']?(?=\s|$)' -or $state.api[0].CommandLine -notmatch '(?:^|\s)--host(?:\s+|=)["'']?127\.0\.0\.1["'']?(?=\s|$)') {
            throw 'An API for this workspace is running with different host/port arguments. Inspect it before restarting.'
        }
        $apiProcess = [System.Diagnostics.Process]::GetProcessById($state.api[0].ProcessId)
        Write-Host "Reusing workspace API process $($apiProcess.Id)."
    }
    Wait-ApiHealthy $apiProcess
    $state = Get-WorkspaceProcesses
    if ($state.api.Count -ne 1 -or $state.api[0].ProcessId -ne $apiProcess.Id) { throw 'API ownership changed during startup. No worker was started.' }
    if ($state.worker.Count -eq 1) {
        $workerProcess = [System.Diagnostics.Process]::GetProcessById($state.worker[0].ProcessId)
        Assert-ProcessRunning $workerProcess 'Worker'
        Write-Host "Reusing workspace worker process $($workerProcess.Id)."
    } else {
        $workerProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','app.jobs') -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dataRoot 'worker.out.log') -RedirectStandardError (Join-Path $dataRoot 'worker.err.log')
        Start-Sleep -Milliseconds 500
        Assert-ProcessRunning $workerProcess 'Worker'
    }
    Assert-ProcessRunning $apiProcess 'API'
    $state = Get-WorkspaceProcesses
    if ($state.api.Count -ne 1 -or $state.api[0].ProcessId -ne $apiProcess.Id -or $state.worker.Count -ne 1 -or $state.worker[0].ProcessId -ne $workerProcess.Id) {
        throw 'Workspace process ownership changed during startup. Inspect data/ logs before restarting.'
    }
    Write-ProcessRecord $state $apiProcess.Id $workerProcess.Id
    Write-Host 'App running: http://127.0.0.1:8000'
    Write-Host 'API reference: http://127.0.0.1:8000/docs'
    Write-Host 'Logs are in data/. Stop with scripts/stop.ps1.'
} finally {
    if ($ownsMutex) { $startMutex.ReleaseMutex() }
    $startMutex.Dispose()
}
