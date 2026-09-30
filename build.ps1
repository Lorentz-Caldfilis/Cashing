$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { Pop-Location; throw 'Create .venv and install requirements-dev.txt first.' }
$work = Join-Path $PSScriptRoot 'work'
New-Item -ItemType Directory -Path $work -Force | Out-Null
$names = @('TEMP','TMP','PYINSTALLER_CONFIG_DIR','MPLCONFIGDIR','QT_API','PYTHONUTF8','PATH')
$saved = @{}
foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    $env:TEMP = $work
    $env:TMP = $work
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $work 'pyinstaller-cache'
    $env:MPLCONFIGDIR = Join-Path $work 'mpl-build'
    $env:QT_API = 'pyside6'
    $env:PYTHONUTF8 = '1'
    # Do not collect incompatible DLLs from unrelated tools on the caller's PATH.
    $basePython = & $python -c "import sys; print(sys.base_prefix)"
    $env:PATH = "$(Split-Path $python);$basePython;$env:SystemRoot\System32;$env:SystemRoot"
    & $python -m PyInstaller --clean --noconfirm --workpath (Join-Path $PSScriptRoot 'build') --distpath (Join-Path $PSScriptRoot 'dist') Cashing.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    # Bind the build to its source; packaging must not label an older dist as HEAD.
    # Git may be outside the isolated DLL search PATH, so restore it for provenance.
    $env:PATH = $saved['PATH']
    $sourceCommit = & git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify source commit' }
    & git diff --quiet HEAD
    $sourceDirty = $LASTEXITCODE -ne 0
    @{ source_commit = $sourceCommit.Trim(); tracked_changes = $sourceDirty } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'dist\Cashing\BUILD_SOURCE.json') -Encoding utf8
    Write-Host 'Built: dist\Cashing\Cashing.exe - distribute the entire Cashing directory.'
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
    Pop-Location
}
