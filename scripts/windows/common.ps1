Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).ProviderPath
}

function Get-DefaultRuntimeRoot {
  return "G:\\electric-ai-runtime"
}

function Get-DefaultPythonEnvPath {
  return "G:\\miniconda3\\envs\\electric-ai-py310"
}

function Get-DefaultPythonExe {
  return Join-Path (Get-DefaultPythonEnvPath) "python.exe"
}

function Get-DefaultCondaBat {
  return "G:\\miniconda3\\condabin\\conda.bat"
}

function Get-DefaultGoExe {
  return "G:\\Golang\\go1.24.0\\bin\\go.exe"
}

function Get-DefaultLegacyProjectRoot {
  return "E:\\毕业设计\\源代码\\Project"
}

function Write-Step {
  param([string]$Message)

  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
  param([string]$Message)

  Write-Host "    $Message" -ForegroundColor DarkGray
}

function Ensure-Directory {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
  }

  return (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Assert-PathExists {
  param(
    [string]$Path,
    [string]$Label
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "$Label not found: $Path"
  }

  return (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Resolve-CommandPath {
  param([string]$CommandName)

  $command = Get-Command $CommandName -ErrorAction Stop
  return $command.Source
}

function Invoke-CheckedCommand {
  param(
    [string]$Label,
    [string]$FilePath,
    [string[]]$Arguments = @(),
    [string]$WorkingDirectory = ""
  )

  Write-Step $Label
  $originalLocation = Get-Location
  try {
    if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
      Set-Location -LiteralPath $WorkingDirectory
    }

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
      throw "$Label failed with exit code $LASTEXITCODE"
    }
  } finally {
    Set-Location $originalLocation
  }
}

function Get-LogsRoot {
  param([string]$RepoRoot)

  return Ensure-Directory (Join-Path $RepoRoot ".runtime-logs")
}

function Get-WindowsLogsRoot {
  param([string]$RepoRoot)

  return Ensure-Directory (Join-Path (Get-LogsRoot -RepoRoot $RepoRoot) "windows")
}

function Wait-HttpReady {
  param(
    [string]$Url,
    [string]$Name,
    [int]$TimeoutSeconds = 60
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

  do {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return
      }
    } catch {
    }

    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)

  throw "Timed out waiting for $Name at $Url"
}

function Get-ListeningProcessInfo {
  param([int]$Port)

  $items = @()
  $processIds = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique
  )

  foreach ($processId in $processIds) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($null -eq $processInfo) {
      continue
    }

    $items += [PSCustomObject]@{
      Port           = $Port
      Id             = [int]$processId
      Name           = [string]$processInfo.Name
      ExecutablePath = [string]$processInfo.ExecutablePath
      CommandLine    = [string]$processInfo.CommandLine
    }
  }

  return $items
}

function Test-ManagedProcessInfo {
  param(
    [pscustomobject]$ProcessInfo,
    [string]$RepoRoot,
    [string]$RuntimeRoot
  )

  $needles = @(
    $RepoRoot,
    (Join-Path $RepoRoot ".runtime-logs"),
    $RuntimeRoot,
    "electric-ai-py310",
    "python-ai-service",
    "web-console",
    "vite",
    "gateway-service",
    "auth-service",
    "model-service",
    "task-service",
    "asset-service",
    "audit-service"
  )
  $haystack = (@($ProcessInfo.ExecutablePath, $ProcessInfo.CommandLine) -join " ").ToLowerInvariant()

  foreach ($needle in $needles) {
    if (-not [string]::IsNullOrWhiteSpace($needle) -and $haystack.Contains($needle.ToLowerInvariant())) {
      return $true
    }
  }

  return $false
}

function Stop-ManagedListeners {
  param(
    [int[]]$Ports,
    [string]$RepoRoot,
    [string]$RuntimeRoot
  )

  $stopped = @()
  foreach ($port in $Ports) {
    foreach ($item in @(Get-ListeningProcessInfo -Port $port)) {
      if (-not (Test-ManagedProcessInfo -ProcessInfo $item -RepoRoot $RepoRoot -RuntimeRoot $RuntimeRoot)) {
        throw "Port $port is occupied by unrelated process $($item.Name) ($($item.Id)): $($item.CommandLine)"
      }

      Stop-Process -Id $item.Id -Force -ErrorAction Stop
      $stopped += $item
    }
  }

  if ($stopped.Count -gt 0) {
    Start-Sleep -Seconds 2
  }

  return $stopped
}

function Find-ManagedProcessesByPattern {
  param(
    [string[]]$Patterns,
    [string]$RepoRoot
  )

  $items = @()
  $normalizedRepoRoot = $RepoRoot.ToLowerInvariant()
  $defaultPythonExe = (Get-DefaultPythonExe).ToLowerInvariant()
  foreach ($processInfo in Get-CimInstance Win32_Process -ErrorAction SilentlyContinue) {
    $haystack = (@($processInfo.ExecutablePath, $processInfo.CommandLine) -join " ").ToLowerInvariant()
    $isManaged = $haystack.Contains($normalizedRepoRoot) -or $haystack.Contains(".runtime-logs")

    foreach ($pattern in $Patterns) {
      if ($haystack.Contains($pattern.ToLowerInvariant())) {
        if (-not $isManaged) {
          $isPythonWorker = $processInfo.ExecutablePath `
            -and $processInfo.ExecutablePath.ToLowerInvariant() -eq $defaultPythonExe `
            -and $haystack.Contains("-m app.worker")
          if (-not $isPythonWorker) {
            break
          }
        }
        $items += [PSCustomObject]@{
          Id             = [int]$processInfo.ProcessId
          Name           = [string]$processInfo.Name
          ExecutablePath = [string]$processInfo.ExecutablePath
          CommandLine    = [string]$processInfo.CommandLine
        }
        break
      }
    }
  }

  return @($items | Sort-Object Id -Unique)
}

function Stop-ManagedProcessesByPattern {
  param(
    [string[]]$Patterns,
    [string]$RepoRoot
  )

  $stopped = @()
  foreach ($item in @(Find-ManagedProcessesByPattern -Patterns $Patterns -RepoRoot $RepoRoot)) {
    Stop-Process -Id $item.Id -Force -ErrorAction SilentlyContinue
    $stopped += $item
  }

  if ($stopped.Count -gt 0) {
    Start-Sleep -Seconds 1
  }

  return $stopped
}

function Assert-PortsFree {
  param([int[]]$Ports)

  foreach ($port in $Ports) {
    if (@(Get-ListeningProcessInfo -Port $port).Count -gt 0) {
      throw "Port $port is still occupied after cleanup."
    }
  }
}

function New-LauncherFile {
  param(
    [string]$Name,
    [string]$LaunchersRoot,
    [string]$WorkingDirectory,
    [hashtable]$Environment,
    [string]$Command
  )

  $null = Ensure-Directory $LaunchersRoot
  $launcherPath = Join-Path $LaunchersRoot "$Name.cmd"
  $lines = @(
    "@echo off",
    "setlocal"
  )

  foreach ($key in ($Environment.Keys | Sort-Object)) {
    $lines += "set ""$key=$([string]$Environment[$key])"""
  }

  $lines += "cd /d ""$WorkingDirectory"""
  $lines += $Command
  Set-Content -LiteralPath $launcherPath -Value ($lines -join "`r`n") -Encoding Default
  return $launcherPath
}

function Start-LoggedLauncher {
  param(
    [string]$Name,
    [string]$LauncherPath,
    [string]$LogsRoot
  )

  $stdoutPath = Join-Path $LogsRoot "$Name.stdout.log"
  $stderrPath = Join-Path $LogsRoot "$Name.stderr.log"
  Remove-Item -LiteralPath $stdoutPath, $stderrPath -ErrorAction SilentlyContinue

  return Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", $LauncherPath) `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath
}

function Assert-ProcessAlive {
  param(
    [System.Diagnostics.Process]$Process,
    [string]$Name
  )

  Start-Sleep -Seconds 2
  if ($Process.HasExited) {
    throw "$Name exited early with code $($Process.ExitCode). Check .runtime-logs/windows/$Name.stderr.log"
  }
}

