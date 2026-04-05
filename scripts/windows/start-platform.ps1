param(
  [string]$ComposeFile = "deploy/docker-compose.dev.yml",
  [string]$GoExe = "",
  [string]$PythonExe = "",
  [string]$RuntimeRoot = "",
  [int]$MySQLPort = 3307,
  [int]$RedisPort = 6380,
  [switch]$SkipWeb,
  [switch]$SkipPythonSetup
)

# 启动本机原生整个平台：
# 1. 复用或拉起 MySQL / Redis
# 2. 构建并启动全部 Go 微服务
# 3. 启动 Python API、Worker 和前端开发服务器
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$runtimeRootPath = if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) { Get-DefaultRuntimeRoot } else { $RuntimeRoot }
$goExePath = if ([string]::IsNullOrWhiteSpace($GoExe)) { Get-DefaultGoExe } else { $GoExe }
$pythonExePath = if ([string]::IsNullOrWhiteSpace($PythonExe)) { Get-DefaultPythonExe } else { $PythonExe }
$goExePath = Assert-PathExists -Path $goExePath -Label "go.exe"
$windowsLogsRoot = Get-WindowsLogsRoot -RepoRoot $repoRoot
$launchersRoot = Ensure-Directory (Join-Path $windowsLogsRoot "launchers")
$binariesRoot = Ensure-Directory (Join-Path $windowsLogsRoot "bin")
$pythonServiceRoot = Join-Path $repoRoot "python-ai-service"
$imageOutputDir = Join-Path $runtimeRootPath "outputs\\images"
$mysqlDsn = "root:root@tcp(127.0.0.1:$MySQLPort)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local"
$redisAddr = "127.0.0.1:$RedisPort"
$redisUrl = "redis://127.0.0.1:$RedisPort/0"
$jwtSecret = "electric-ai-secret"
$npmCmd = Resolve-CommandPath -CommandName "npm.cmd"

if (-not $SkipPythonSetup -or -not (Test-Path -LiteralPath $pythonExePath)) {
  & (Join-Path $PSScriptRoot "setup-python-runtime.ps1") -PythonEnvPath (Split-Path -Parent $pythonExePath) -RuntimeRoot $runtimeRootPath
}

$pythonExePath = Assert-PathExists -Path $pythonExePath -Label "python.exe"
$env:GOROOT = Split-Path -Parent (Split-Path -Parent $goExePath)

$mysqlListening = @(Get-ListeningProcessInfo -Port $MySQLPort).Count -gt 0
$redisListening = @(Get-ListeningProcessInfo -Port $RedisPort).Count -gt 0

if ($mysqlListening -and $redisListening) {
  Write-Step "Reuse existing MySQL and Redis listeners"
} else {
  Write-Step "Start MySQL and Redis"
  & (Join-Path $repoRoot "scripts\\dev-up.ps1") -ComposeFile $ComposeFile -TimeoutSeconds 180
}

Write-Step "Check runtime model directories"
$env:ELECTRIC_AI_RUNTIME_ROOT = $runtimeRootPath
Invoke-CheckedCommand `
  -Label "Check runtime model directories" `
  -FilePath $pythonExePath `
  -Arguments @("scripts/download_models.py", "--all", "--check") `
  -WorkingDirectory $pythonServiceRoot

$portsToFree = @(8081, 8082, 8083, 8084, 8085, 8080, 8090)
if (-not $SkipWeb) {
  $portsToFree += 5173
}

$null = Stop-ManagedProcessesByPattern -Patterns @("app.worker", "worker.cmd") -RepoRoot $repoRoot
$stoppedListeners = @(Stop-ManagedListeners -Ports $portsToFree -RepoRoot $repoRoot -RuntimeRoot $runtimeRootPath)
if ($stoppedListeners.Count -gt 0) {
  Write-Info "Cleaned up stale platform listeners."
}
Assert-PortsFree -Ports $portsToFree

$goServices = @(
  @{
    Name        = "auth-service"
    PackagePath = ".\\services\\auth-service\\cmd\\server"
    Port        = 8081
    HealthUrl   = "http://127.0.0.1:8081/health"
    Environment = @{
      APP_NAME   = "auth-service"
      HTTP_PORT  = "8081"
      MYSQL_DSN  = $mysqlDsn
      REDIS_ADDR = $redisAddr
      JWT_SECRET = $jwtSecret
    }
  },
  @{
    Name        = "model-service"
    PackagePath = ".\\services\\model-service\\cmd\\server"
    Port        = 8082
    HealthUrl   = "http://127.0.0.1:8082/health"
    Environment = @{
      APP_NAME   = "model-service"
      HTTP_PORT  = "8082"
      MYSQL_DSN  = $mysqlDsn
      REDIS_ADDR = $redisAddr
      JWT_SECRET = $jwtSecret
    }
  },
  @{
    Name        = "task-service"
    PackagePath = ".\\services\\task-service\\cmd\\server"
    Port        = 8083
    HealthUrl   = "http://127.0.0.1:8083/health"
    Environment = @{
      APP_NAME   = "task-service"
      HTTP_PORT  = "8083"
      MYSQL_DSN  = $mysqlDsn
      REDIS_ADDR = $redisAddr
      JWT_SECRET = $jwtSecret
    }
  },
  @{
    Name        = "asset-service"
    PackagePath = ".\\services\\asset-service\\cmd\\server"
    Port        = 8084
    HealthUrl   = "http://127.0.0.1:8084/health"
    Environment = @{
      APP_NAME   = "asset-service"
      HTTP_PORT  = "8084"
      MYSQL_DSN  = $mysqlDsn
      REDIS_ADDR = $redisAddr
      JWT_SECRET = $jwtSecret
    }
  },
  @{
    Name        = "audit-service"
    PackagePath = ".\\services\\audit-service\\cmd\\server"
    Port        = 8085
    HealthUrl   = "http://127.0.0.1:8085/health"
    Environment = @{
      APP_NAME   = "audit-service"
      HTTP_PORT  = "8085"
      MYSQL_DSN  = $mysqlDsn
      REDIS_ADDR = $redisAddr
      JWT_SECRET = $jwtSecret
    }
  },
  @{
    Name        = "gateway-service"
    PackagePath = ".\\services\\gateway-service\\cmd\\server"
    Port        = 8080
    HealthUrl   = "http://127.0.0.1:8080/health"
    Environment = @{
      APP_NAME          = "gateway-service"
      HTTP_PORT         = "8080"
      JWT_SECRET        = $jwtSecret
      AUTH_SERVICE_URL  = "http://127.0.0.1:8081"
      MODEL_SERVICE_URL = "http://127.0.0.1:8082"
      TASK_SERVICE_URL  = "http://127.0.0.1:8083"
      ASSET_SERVICE_URL = "http://127.0.0.1:8084"
      AUDIT_SERVICE_URL = "http://127.0.0.1:8085"
      IMAGE_OUTPUT_DIR  = $imageOutputDir
    }
  }
)

foreach ($service in $goServices) {
  $binaryPath = Join-Path $binariesRoot "$($service.Name).exe"
  Invoke-CheckedCommand `
    -Label "Build $($service.Name)" `
    -FilePath $goExePath `
    -Arguments @("build", "-o", $binaryPath, $service.PackagePath) `
    -WorkingDirectory $repoRoot

  $launcherPath = New-LauncherFile `
    -Name $service.Name `
    -LaunchersRoot $launchersRoot `
    -WorkingDirectory $repoRoot `
    -Environment $service.Environment `
    -Command "`"$binaryPath`""

  Write-Step "Start $($service.Name)"
  $process = Start-LoggedLauncher -Name $service.Name -LauncherPath $launcherPath -LogsRoot $windowsLogsRoot
  Assert-ProcessAlive -Process $process -Name $service.Name
  Wait-HttpReady -Url $service.HealthUrl -Name $service.Name -TimeoutSeconds 60
}

$pythonEnvironment = @{
  ELECTRIC_AI_RUNTIME_ROOT = $runtimeRootPath
  HF_HOME                  = Join-Path $runtimeRootPath "hf-home"
  TASK_SERVICE_BASE_URL    = "http://127.0.0.1:8083"
  ASSET_SERVICE_BASE_URL   = "http://127.0.0.1:8084"
  AUDIT_SERVICE_BASE_URL   = "http://127.0.0.1:8085"
  MODEL_SERVICE_BASE_URL   = "http://127.0.0.1:8082"
  REDIS_URL                = $redisUrl
  PYTHONIOENCODING         = "utf-8"
}

$pythonApiLauncher = New-LauncherFile `
  -Name "python-api" `
  -LaunchersRoot $launchersRoot `
  -WorkingDirectory $pythonServiceRoot `
  -Environment $pythonEnvironment `
  -Command "`"$pythonExePath`" -m uvicorn app.main:app --host 127.0.0.1 --port 8090"

Write-Step "Start python-ai-service API"
$pythonApiProcess = Start-LoggedLauncher -Name "python-api" -LauncherPath $pythonApiLauncher -LogsRoot $windowsLogsRoot
Assert-ProcessAlive -Process $pythonApiProcess -Name "python-api"
Wait-HttpReady -Url "http://127.0.0.1:8090/health" -Name "python-ai-service API" -TimeoutSeconds 60

$workerLauncher = New-LauncherFile `
  -Name "python-worker" `
  -LaunchersRoot $launchersRoot `
  -WorkingDirectory $pythonServiceRoot `
  -Environment $pythonEnvironment `
  -Command "`"$pythonExePath`" -m app.worker"

Write-Step "Start python-ai-service Worker"
$workerProcess = Start-LoggedLauncher -Name "python-worker" -LauncherPath $workerLauncher -LogsRoot $windowsLogsRoot
Assert-ProcessAlive -Process $workerProcess -Name "python-worker"

if (-not $SkipWeb) {
  if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "web-console\\node_modules"))) {
    Invoke-CheckedCommand `
      -Label "Install web-console dependencies" `
      -FilePath $npmCmd `
      -Arguments @("--prefix", "web-console", "install") `
      -WorkingDirectory $repoRoot
  }

  $webLauncher = New-LauncherFile `
    -Name "web-console" `
    -LaunchersRoot $launchersRoot `
    -WorkingDirectory $repoRoot `
    -Environment @{} `
    -Command "`"$npmCmd`" --prefix web-console run dev -- --host 127.0.0.1 --port 5173 --strictPort"

  Write-Step "Start web-console"
  $webProcess = Start-LoggedLauncher -Name "web-console" -LauncherPath $webLauncher -LogsRoot $windowsLogsRoot
  Assert-ProcessAlive -Process $webProcess -Name "web-console"
  Wait-HttpReady -Url "http://127.0.0.1:5173" -Name "web-console" -TimeoutSeconds 60
}

Write-Step "Platform started"
Write-Info "Gateway: http://127.0.0.1:8080"
Write-Info "Python runtime: http://127.0.0.1:8090"
if (-not $SkipWeb) {
  Write-Info "Web console: http://127.0.0.1:5173"
}
Write-Info "Logs: $windowsLogsRoot"
Write-Info "MySQL: 127.0.0.1:$MySQLPort"
Write-Info "Redis: 127.0.0.1:$RedisPort"

