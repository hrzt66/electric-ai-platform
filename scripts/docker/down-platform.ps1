param(
  [string]$ComposeFile = "deploy/docker-compose.platform.yml",
  [switch]$RemoveVolumes
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

$arguments = @("compose", "-f", $composePath, "down")
if ($RemoveVolumes) {
  $arguments += "-v"
}

Invoke-CheckedCommand `
  -Label "Stop docker platform" `
  -FilePath $dockerExe `
  -Arguments $arguments `
  -WorkingDirectory $repoRoot
