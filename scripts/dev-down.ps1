param(
  [string]$ComposeFile = "deploy/docker-compose.dev.yml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ComposeFilePath {
  param([string]$ComposeFile)

  $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
  $candidatePath = if ([System.IO.Path]::IsPathRooted($ComposeFile)) {
    $ComposeFile
  } else {
    Join-Path $repoRoot $ComposeFile
  }

  if (-not (Test-Path -LiteralPath $candidatePath)) {
    throw "Compose file not found: $candidatePath"
  }

  return (Resolve-Path -LiteralPath $candidatePath).ProviderPath
}

try {
  $composeFilePath = Resolve-ComposeFilePath -ComposeFile $ComposeFile
  & docker compose -f $composeFilePath down -v
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed with exit code ${LASTEXITCODE}: docker compose -f $composeFilePath down -v"
  }

  Write-Host "Development dependencies are stopped."
} catch {
  Write-Error $_
  exit 1
}
