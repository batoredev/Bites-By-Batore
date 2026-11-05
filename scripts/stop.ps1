$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot 'data\processes.json'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'No script-managed processes recorded.'; exit 0 }
$record = Get-Content -LiteralPath $pidFile | ConvertFrom-Json
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
[array]::Reverse($ownedProcesses)
foreach ($owned in $ownedProcesses) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($owned.id)" -ErrorAction SilentlyContinue
    if ($process -and ($process.CommandLine -match 'app\.main:app|app\.jobs') -and [math]::Abs(($process.CreationDate.ToUniversalTime() - ([datetime]$owned.created).ToUniversalTime()).TotalSeconds) -lt 1) {
        Stop-Process -Id $owned.id -ErrorAction SilentlyContinue
        Write-Host "Stopped Batore process $($owned.id)"
    }
}
Remove-Item -LiteralPath $pidFile
