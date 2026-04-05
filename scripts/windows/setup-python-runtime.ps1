param(
  [string]$CondaBat = "",
  [string]$PythonEnvPath = "",
  [string]$RuntimeRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$runtimeRoot = if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) { Get-DefaultRuntimeRoot } else { $RuntimeRoot }
$condaBatPath = if ([string]::IsNullOrWhiteSpace($CondaBat)) { Get-DefaultCondaBat } else { $CondaBat }
$pythonEnvRoot = if ([string]::IsNullOrWhiteSpace($PythonEnvPath)) { Get-DefaultPythonEnvPath } else { $PythonEnvPath }
$requirementsPath = Assert-PathExists -Path (Join-Path $repoRoot "python-ai-service\\requirements.txt") -Label "python requirements"
$pythonExePath = Join-Path $pythonEnvRoot "python.exe"

$condaBatPath = Assert-PathExists -Path $condaBatPath -Label "conda.bat"

if (-not (Test-Path -LiteralPath $pythonExePath)) {
  Invoke-CheckedCommand `
    -Label "Create electric-ai-py310 environment" `
    -FilePath $condaBatPath `
    -Arguments @("create", "-y", "-p", $pythonEnvRoot, "python=3.10") `
    -WorkingDirectory $repoRoot
}

$pythonExePath = Assert-PathExists -Path $pythonExePath -Label "python.exe"
$env:ELECTRIC_AI_RUNTIME_ROOT = $runtimeRoot

Invoke-CheckedCommand `
  -Label "Upgrade Python packaging tools" `
  -FilePath $pythonExePath `
  -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel") `
  -WorkingDirectory $repoRoot

Invoke-CheckedCommand `
  -Label "Install python-ai-service dependencies" `
  -FilePath $pythonExePath `
  -Arguments @("-m", "pip", "install", "-r", $requirementsPath) `
  -WorkingDirectory $repoRoot

Invoke-CheckedCommand `
  -Label "Run Python runtime probe" `
  -FilePath $pythonExePath `
  -Arguments @("scripts/runtime_probe.py") `
  -WorkingDirectory (Join-Path $repoRoot "python-ai-service")

Write-Step "Python runtime ready"
Write-Info "Python: $pythonExePath"
Write-Info "Runtime root: $runtimeRoot"

