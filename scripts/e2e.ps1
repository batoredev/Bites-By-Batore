# Run the Playwright suite against a throwaway demo database, never the live one.
# Starts its own API (port 8010) and job worker, runs the tests, then stops both.
# Usage: .\scripts\e2e.ps1                                   (all demo-mode tests)
#        .\scripts\e2e.ps1 tests\research.spec.ts
#        .\scripts\e2e.ps1 -Mode local tests\local-research.spec.ts   (local mode, still a throwaway database)
param(
    [ValidateSet('demo', 'local')] [string] $Mode = 'demo',
    [Parameter(ValueFromRemainingArguments = $true)] [string[]] $Specs
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$web = Join-Path $root 'web'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$runDir = Join-Path $root 'data\e2e'
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$db = Join-Path $runDir "run-$stamp.db"
$port = 8010

if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $port is busy. Stop whatever is using it; the test API never shares a port with the real app."
}

# Child processes inherit these; the real app on port 8000 is untouched.
$env:APP_MODE = $Mode
$env:DATABASE_URL = 'sqlite:///' + ($db -replace '\\', '/')
$api = $null
$worker = $null
try {
    Push-Location $web
    $ErrorActionPreference = 'Continue'
    npm run build | Out-Null
    $built = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Pop-Location
    if ($built -ne 0) { throw 'Web build failed.' }

    $api = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$port") `
        -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runDir "api-$stamp.out.log") -RedirectStandardError (Join-Path $runDir "api-$stamp.err.log")
    $healthy = $false
    foreach ($i in 1..60) {
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 2
            if ($health.mode -ne $Mode) { throw "Test API came up in '$($health.mode)' mode instead of '$Mode'; refusing to run tests." }
            $healthy = $true
            break
        } catch [System.Net.WebException] { Start-Sleep -Milliseconds 500 }
    }
    if (-not $healthy) { throw 'Test API did not become healthy.' }

    $worker = Start-Process -FilePath $python -ArgumentList @('-m', 'app.jobs') -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runDir "worker-$stamp.out.log") -RedirectStandardError (Join-Path $runDir "worker-$stamp.err.log")

    Push-Location $web
    $env:BATORE_TEST_BASE_URL = "http://127.0.0.1:$port"
    # Node prints warnings on stderr; under 'Stop' Windows PowerShell would treat them as fatal.
    $ErrorActionPreference = 'Continue'
    npx playwright test @Specs
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Pop-Location
    exit $code
} finally {
    foreach ($p in @($worker, $api)) {
        if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item Env:APP_MODE, Env:DATABASE_URL, Env:BATORE_TEST_BASE_URL -ErrorAction SilentlyContinue
}
