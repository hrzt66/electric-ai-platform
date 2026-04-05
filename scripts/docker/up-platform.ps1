param(
  [string]$ComposeFile = "deploy/docker-compose.platform.yml",
  [switch]$NoBuild
)

# 启动 Docker 编排版平台，并等待网关、Python 运行时和前端容器健康可用。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\\windows\\common.ps1")

$repoRoot = Get-RepoRoot
$composePath = Join-Path $repoRoot $ComposeFile
$dockerExe = Resolve-CommandPath -CommandName "docker.exe"

if (-not (Test-Path -LiteralPath $composePath)) {
  throw "Compose file not found: $composePath"
}

$arguments = @("compose", "-f", $composePath, "up", "-d")
if (-not $NoBuild) {
  $arguments += "--build"
}

Invoke-CheckedCommand `
  -Label "Start docker platform" `
  -FilePath $dockerExe `
  -Arguments $arguments `
  -WorkingDirectory $repoRoot

Write-Step "Wait docker services"
Wait-HttpReady -Url "http://127.0.0.1:18080/health" -Name "gateway-service" -TimeoutSeconds 300
Wait-HttpReady -Url "http://127.0.0.1:18090/health" -Name "python-ai-service" -TimeoutSeconds 300
Wait-HttpReady -Url "http://127.0.0.1:18088" -Name "web-console" -TimeoutSeconds 300

Write-Step "Docker platform started"
Write-Info "Gateway: http://127.0.0.1:18080"
Write-Info "Python runtime: http://127.0.0.1:18090"
Write-Info "Web console: http://127.0.0.1:18088"
