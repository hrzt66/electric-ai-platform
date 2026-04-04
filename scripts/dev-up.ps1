param(
  [string]$ComposeFile = "deploy/docker-compose.dev.yml",
  [int]$TimeoutSeconds = 120
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

function Invoke-DockerCompose {
  param(
    [string]$ComposeFilePath,
    [string[]]$Arguments
  )

  & docker compose -f $ComposeFilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed with exit code ${LASTEXITCODE}: docker compose -f $ComposeFilePath $($Arguments -join ' ')"
  }
}

function Get-ServiceContainerId {
  param(
    [string]$ComposeFilePath,
    [string]$Service
  )

  $containerIdOutput = & docker compose -f $ComposeFilePath ps -q $Service
  if ($LASTEXITCODE -ne 0) {
    throw "Unable to determine container id for service '$Service'."
  }
  $containerId = "$($containerIdOutput | Select-Object -First 1)".Trim()
  if ([string]::IsNullOrWhiteSpace($containerId)) {
    throw "Service '$Service' is not running."
  }

  return $containerId
}

function Wait-ForServiceHealth {
  param(
    [string]$ComposeFilePath,
    [string]$Service,
    [int]$TimeoutSeconds
  )

  $containerId = Get-ServiceContainerId -ComposeFilePath $ComposeFilePath -Service $Service
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

  do {
    $statusOutput = & docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $containerId
    if ($LASTEXITCODE -ne 0) {
      throw "Unable to inspect container health for service '$Service'."
    }
    $status = "$($statusOutput | Select-Object -First 1)".Trim()

    if ($status -eq "healthy") {
      Write-Host "$Service is healthy."
      return
    }

    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)

  throw "Timed out waiting for service '$Service' to become healthy."
}

try {
  $composeFilePath = Resolve-ComposeFilePath -ComposeFile $ComposeFile
  Invoke-DockerCompose -ComposeFilePath $composeFilePath -Arguments @("up", "-d", "mysql", "redis")
  Wait-ForServiceHealth -ComposeFilePath $composeFilePath -Service "mysql" -TimeoutSeconds $TimeoutSeconds
  Wait-ForServiceHealth -ComposeFilePath $composeFilePath -Service "redis" -TimeoutSeconds $TimeoutSeconds
  Write-Host "Development dependencies are ready."
} catch {
  Write-Error $_
  exit 1
}
