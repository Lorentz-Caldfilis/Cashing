$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath($PSScriptRoot + '\..')
$testRoot = [IO.Path]::GetFullPath((Join-Path $project 'work\中文 空格 解压只读'))
if (!$testRoot.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid test directory.' }
if (Test-Path -LiteralPath $testRoot) { throw 'Use a new extraction directory.' }
Expand-Archive -LiteralPath (Join-Path $project 'release\Cashing-v1.1.0-windows.zip') -DestinationPath $testRoot
$install = Join-Path $testRoot 'Cashing'
$original = Get-Acl -LiteralPath $install
$restricted = Get-Acl -LiteralPath $install
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
$rule = [Security.AccessControl.FileSystemAccessRule]::new(
    $identity, [Security.AccessControl.FileSystemRights]::Write,
    [Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit',
    [Security.AccessControl.PropagationFlags]::None,
    [Security.AccessControl.AccessControlType]::Deny)
$restricted.AddAccessRule($rule)
$denied = $false
try {
    Set-Acl -LiteralPath $install -AclObject $restricted
    try { [IO.File]::WriteAllText((Join-Path $install 'write-probe.txt'), 'probe') }
    catch [UnauthorizedAccessException] { $denied = $true }
    if (!$denied) { throw 'Installation is not actually read-only.' }
    $env:PYTHONUTF8 = '1'
    & (Join-Path $project '.venv\Scripts\python.exe') (Join-Path $project 'scripts\verify_release.py') --phase frozen --install $install --label audit-readonly-extracted
    if ($LASTEXITCODE -ne 0) { throw 'Extracted read-only EXE verification failed.' }
} finally {
    Set-Acl -LiteralPath $install -AclObject $original
}
@{status='PASS'; writeActuallyDenied=$denied; aclRestored=$true; install=$install} |
    ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $project 'work\readonly-install-result.json')
