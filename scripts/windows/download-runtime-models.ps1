param(
  [string[]]$Model = @(),
  [switch]$All,
  [switch]$CheckOnly,
  [string]$PythonExe = "",
  [string]$RuntimeRoot = "",
  [string]$LegacyProjectRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$pythonExePath = if ([string]::IsNullOrWhiteSpace($PythonExe)) { Get-DefaultPythonExe } else { $PythonExe }
$pythonExePath = Assert-PathExists -Path $pythonExePath -Label "python.exe"
$runtimeRootPath = if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) { Get-DefaultRuntimeRoot } else { $RuntimeRoot }
$legacyRootPath = if ([string]::IsNullOrWhiteSpace($LegacyProjectRoot)) { Get-DefaultLegacyProjectRoot } else { $LegacyProjectRoot }
$pythonServiceRoot = Join-Path $repoRoot "python-ai-service"

$env:ELECTRIC_AI_RUNTIME_ROOT = $runtimeRootPath
$env:ELECTRIC_AI_LEGACY_ROOT = $legacyRootPath

$arguments = @("scripts/download_models.py")
if ($CheckOnly) {
  $arguments += "--check"
}

if ($All -or $Model.Count -eq 0) {
  $arguments += "--all"
} else {
  foreach ($item in $Model) {
    $arguments += @("--model", $item)
  }
}

Invoke-CheckedCommand `
  -Label "Run model preparation script" `
  -FilePath $pythonExePath `
  -Arguments $arguments `
  -WorkingDirectory $pythonServiceRoot

Invoke-CheckedCommand `
  -Label "Print runtime status" `
  -FilePath $pythonExePath `
  -Arguments @("scripts/runtime_probe.py") `
  -WorkingDirectory $pythonServiceRoot

Write-Step "Model preparation finished"
Write-Info "Runtime root: $runtimeRootPath"
Write-Info "Legacy source root is configured."

