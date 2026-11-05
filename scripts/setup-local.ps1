param([switch]$SkipModels)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
uv sync --project backend --frozen
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
uv run --project backend playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Research browser installation failed.' }
if (-not $SkipModels) {
    $ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (-not (Test-Path -LiteralPath $ollamaExe)) {
        $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaCommand) { throw 'Install Ollama from https://ollama.com/download/windows, then rerun this script.' }
        $ollamaExe = $ollamaCommand.Source
    }
    & $ollamaExe pull qwen3-vl:2b-instruct
    if ($LASTEXITCODE -ne 0) { throw 'Local vision model download failed.' }
    Push-Location backend
    try {
        uv run python -c "from faster_whisper import WhisperModel; from app.config import ROOT; WhisperModel('base', device='cpu', compute_type='int8', download_root=str(ROOT / 'data' / 'models')); print('Local speech model ready')"
        if ($LASTEXITCODE -ne 0) { throw 'Local speech model download failed.' }
    } finally { Pop-Location }
}
Write-Host 'Local model dependencies ready. Local research configuration is documented in docs/LOCAL_RESEARCH.md.'
Write-Host 'Start the API and worker with scripts/start.ps1. Downloads are separate from inference; inference stays local.'
