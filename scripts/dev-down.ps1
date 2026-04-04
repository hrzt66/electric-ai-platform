param(
  [string]$ComposeFile = "deploy/docker-compose.dev.yml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
}

function Resolve-ComposeFilePath {
  param([string]$ComposeFile)

  $repoRoot = Resolve-RepoRoot
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

function Get-ComposeProjectName {
  param([string]$RepoRoot)

  $normalizedRoot = $RepoRoot.TrimEnd('\', '/').Replace('\', '/').ToLowerInvariant()
  $sha256 = [System.Security.Cryptography.SHA256]::Create()
  try {
    $hashBytes = $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($normalizedRoot))
  } finally {
    $sha256.Dispose()
  }

  $hash = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLowerInvariant()
  return "electric-ai-$($hash.Substring(0, 12))"
}

try {
  $repoRoot = Resolve-RepoRoot
  $composeFilePath = Resolve-ComposeFilePath -ComposeFile $ComposeFile
  $composeProjectName = Get-ComposeProjectName -RepoRoot $repoRoot

  & docker compose -p $composeProjectName -f $composeFilePath down -v
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed with exit code ${LASTEXITCODE}: docker compose -p $composeProjectName -f $composeFilePath down -v"
  }

  Write-Host "Development dependencies are stopped."
} catch {
  Write-Error $_
  exit 1
}
