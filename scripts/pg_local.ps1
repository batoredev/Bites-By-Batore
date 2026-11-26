# Private local PostgreSQL 17 for rehearsals (week 1, item 1.10).
# Portable binaries in %LOCALAPPDATA%\Batore\pgsql17, data in data\postgres (git-ignored).
# Listens on 127.0.0.1:5433 only; password auth with a random password kept in
# data\postgres-password.txt (git-ignored). No Windows service, no admin rights.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\pg_local.ps1 init|start|stop|status
param([Parameter(Mandatory = $true)][ValidateSet("init", "start", "stop", "status")][string]$Action)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $env:LOCALAPPDATA "Batore\pgsql17\pgsql\bin"
$data = Join-Path $root "data\postgres"
$secret = Join-Path $root "data\postgres-password.txt"
$log = Join-Path $root "data\postgres.log"
$port = 5433

if (-not (Test-Path (Join-Path $bin "pg_ctl.exe"))) { throw "PostgreSQL binaries not found in $bin" }

switch ($Action) {
    "init" {
        if (Test-Path (Join-Path $data "PG_VERSION")) { "already initialised: $data"; break }
        if (-not (Test-Path $secret)) {
            $bytes = New-Object byte[] 24
            [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
            $pw = ([Convert]::ToBase64String($bytes)) -replace '[+/=]', 'x'
            Set-Content -Path $secret -Value $pw -NoNewline -Encoding ascii
        }
        & (Join-Path $bin "initdb.exe") -D $data -U batore --pwfile=$secret --auth=scram-sha-256 -E UTF8 --locale=C | Out-Null
        Add-Content (Join-Path $data "postgresql.conf") "`nlisten_addresses = '127.0.0.1'`nport = $port`n"
        "initialised $data (user batore, port $port, 127.0.0.1 only)"
    }
    "start" {
        # Launched detached: the server inherits console handles, so calling pg_ctl
        # directly never returns on Windows. Wait for readiness instead.
        Start-Process -FilePath (Join-Path $bin "pg_ctl.exe") -ArgumentList @("-D", "`"$data`"", "-l", "`"$log`"", "start") -WindowStyle Hidden
        foreach ($i in 1..30) {
            & (Join-Path $bin "pg_isready.exe") -h 127.0.0.1 -p $port -q
            if ($LASTEXITCODE -eq 0) { "started on 127.0.0.1:$port"; return }
            Start-Sleep -Seconds 1
        }
        throw "PostgreSQL did not become ready; see $log"
    }
    "stop" { & (Join-Path $bin "pg_ctl.exe") -D $data -w stop -m fast }
    "status" { & (Join-Path $bin "pg_ctl.exe") -D $data status }
}
