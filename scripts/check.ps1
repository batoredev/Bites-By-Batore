$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'backend')
try {
    uv run ruff check app tests --select F
    if ($LASTEXITCODE -ne 0) { throw 'Python static checks failed.' }
    uv run pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
} finally { Pop-Location }
Push-Location (Join-Path $projectRoot 'web')
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
} finally { Pop-Location }
Write-Host 'Static checks, backend tests and production build passed.'
Write-Host 'With the local app running, also run: cd web; npm run test:e2e'
