$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot 'data\processes.json'
if (Test-Path -LiteralPath $pidFile) { $record = Get-Content -LiteralPath $pidFile | ConvertFrom-Json }
else { $record = [pscustomobject]@{ processes=@(); api=0; worker=0; started=(Get-Date).ToString('o') } }
$ownedProcesses = @($record.processes)
if (-not $record.processes) {
    # Compatibility with the first launcher record, including Python's redirector child.
    $ownedProcesses = @()
    foreach ($rootPid in @($record.api, $record.worker)) {
        $rootProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$rootPid" -ErrorAction SilentlyContinue
        if ($rootProcess -and ($rootProcess.CommandLine -match 'app\.main:app|app\.jobs') -and $rootProcess.CreationDate -ge ([datetime]$record.started).AddSeconds(-60) -and $rootProcess.CreationDate -le ([datetime]$record.started).AddSeconds(5)) {
            foreach ($owned in @($rootProcess) + @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$rootPid")) {
                $ownedProcesses += [pscustomobject]@{ id=$owned.ProcessId; created=$owned.CreationDate.ToUniversalTime().ToString('o') }
            }
        }
    }
}
# Recover this workspace's Python redirector trees even when an older launcher
# record was replaced. Never match unrelated Python workers by module name alone.
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$allProcesses = @(Get-CimInstance Win32_Process)
foreach ($rootProcess in $allProcesses) {
    if ($rootProcess.ExecutablePath -ieq $pythonExe -and $rootProcess.CommandLine -match 'app\.main:app|app\.jobs') {
        foreach ($owned in @($rootProcess) + @($allProcesses | Where-Object { $_.ParentProcessId -eq $rootProcess.ProcessId -and $_.CommandLine -match 'app\.main:app|app\.jobs' })) {
            if ($owned.ProcessId -notin @($ownedProcesses | ForEach-Object { $_.id })) {
                $ownedProcesses += [pscustomobject]@{ id=$owned.ProcessId; created=$owned.CreationDate.ToUniversalTime().ToString('o') }
            }
        }
    }
}
[array]::Reverse($ownedProcesses)
foreach ($owned in $ownedProcesses) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($owned.id)" -ErrorAction SilentlyContinue
    if ($process -and ($process.CommandLine -match 'app\.main:app|app\.jobs') -and [math]::Abs(($process.CreationDate.ToUniversalTime() - ([datetime]$owned.created).ToUniversalTime()).TotalSeconds) -lt 1) {
        Stop-Process -Id $owned.id -ErrorAction SilentlyContinue
        Write-Host "Stopped Batore process $($owned.id)"
    }
}
if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile }
