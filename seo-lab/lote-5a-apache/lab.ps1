param(
    [switch]$Build,
    [string]$Only
)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Docker não encontrado. Nenhuma instalação será feita.' }
    if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) { throw 'Python não encontrado. Nenhuma instalação será feita.' }
    if (-not (Test-Path -LiteralPath 'results/lab-metadata.json')) {
        & python.exe prepare.py
        if ($LASTEXITCODE -ne 0) { throw 'Preparação não concluída.' }
    }
    $runArgs = @('run_lab.py')
    if ($Build) { $runArgs += '--build' }
    if ($Only) { $runArgs += @('--only', $Only) }
    & python.exe @runArgs
    $runExit = $LASTEXITCODE
    if (Test-Path -LiteralPath 'results/summary.json') {
        & python.exe write_report.py
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar relatório.' }
    }
    if ($runExit -ne 0) { throw 'Execução incompleta: consultar os resultados e timestamps; não presumir aprovação.' }
} finally {
    Pop-Location
}
