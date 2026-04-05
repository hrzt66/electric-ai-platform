param(
  [string]$ComposeFile = "deploy/docker-compose.platform.yml",
  [string[]]$Model = @(),
  [switch]$All,
  [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\\windows\\common.ps1")

$repoRoot = Get-RepoRoot
$composePath = Join-Path $repoRoot $ComposeFile
$dockerExe = Resolve-CommandPath -CommandName "docker.exe"

if (-not (Test-Path -LiteralPath $composePath)) {
  throw "Compose file not found: $composePath"
}

$arguments = @("compose", "-f", $composePath, "run", "--rm", "python-ai-service", "python3", "scripts/download_models.py")

if ($All -or $Model.Count -eq 0) {
  $arguments += "--all"
}

foreach ($item in $Model) {
  $arguments += @("--model", $item)
}

if ($CheckOnly) {
  $arguments += "--check"
}

Invoke-CheckedCommand `
  -Label "Download docker runtime models" `
  -FilePath $dockerExe `
  -Arguments $arguments `
  -WorkingDirectory $repoRoot
