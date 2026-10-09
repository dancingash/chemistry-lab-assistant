# Compatibility wrapper for the portable Python installer.
param(
    [string]$SourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$CodexSkillsRoot = (Join-Path $env:USERPROFILE '.codex\skills'),
    [string]$Python = 'python',
    [string]$DataDir = ''
)
$ErrorActionPreference = 'Stop'
$installArgs = @((Join-Path $SourceRoot 'scripts\install.py'), '--source', $SourceRoot, '--skills-dir', $CodexSkillsRoot)
if ($DataDir) { $installArgs += @('--data-dir', $DataDir) }
& $Python @installArgs
if ($LASTEXITCODE -ne 0) { throw 'lab-rd installation failed' }
