param(
  [string]$GatewayBaseUrl = "http://127.0.0.1:18080",
  [string]$PythonRuntimeBaseUrl = "http://127.0.0.1:18090",
  [string]$ModelName = "unipic2-kontext",
  [int]$TimeoutSeconds = 1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\\windows\\common.ps1")

Write-Step "Check docker gateway and python runtime"
Wait-HttpReady -Url "$GatewayBaseUrl/health" -Name "gateway" -TimeoutSeconds 120
Wait-HttpReady -Url "$PythonRuntimeBaseUrl/health" -Name "python runtime" -TimeoutSeconds 120

$runtimeStatus = Invoke-RestMethod -Uri "$PythonRuntimeBaseUrl/runtime/status" -Method Get
$runtimeModel = @($runtimeStatus.models | Where-Object { $_.name -eq $ModelName }) | Select-Object -First 1
if ($null -eq $runtimeModel) {
  throw "Python runtime did not expose model $ModelName."
}

if ($runtimeModel.status -notin @("available", "experimental")) {
  throw "Model $ModelName is not ready: $($runtimeModel.status)"
}

Write-Step "Login through docker gateway"
$login = Invoke-RestMethod `
  -Method Post `
  -Uri "$GatewayBaseUrl/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123456"}'

if (-not $login.data.access_token) {
  throw "Login failed: missing access token."
}

$headers = @{
  Authorization = "Bearer $($login.data.access_token)"
}

$models = Invoke-RestMethod -Method Get -Uri "$GatewayBaseUrl/api/v1/models" -Headers $headers
$generationModel = @($models.data | Where-Object { $_.model_name -eq $ModelName }) | Select-Object -First 1
if ($null -eq $generationModel) {
  throw "Gateway did not return model $ModelName."
}

$seed = [int](Get-Date -UFormat %s)
$payload = @{
  prompt          = "A realistic 500kV substation control hall, cinematic industrial lighting, ultra detailed"
  negative_prompt = "blurry, low quality, distorted wires"
  model_name      = $ModelName
  seed            = $seed
  steps           = 20
  guidance_scale  = 4.0
  width           = 512
  height          = 512
  num_images      = 1
} | ConvertTo-Json

Write-Step "Submit docker generation job"
$task = Invoke-RestMethod `
  -Method Post `
  -Uri "$GatewayBaseUrl/api/v1/tasks/generate" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $payload

$jobId = [int64]$task.data.id
if ($jobId -le 0) {
  throw "Job creation failed."
}

Write-Info "Job ID: $jobId"

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
  Start-Sleep -Seconds 5
  $detail = Invoke-RestMethod -Method Get -Uri "$GatewayBaseUrl/api/v1/tasks/$jobId" -Headers $headers
  $status = [string]$detail.data.status
  $stage = [string]$detail.data.stage
  Write-Info "Task status: $status / $stage"

  if ($status -eq "failed") {
    throw "Job failed: $($detail.data.error_message)"
  }
} while ($status -ne "completed" -and (Get-Date) -lt $deadline)

if ($status -ne "completed") {
  throw "Job did not finish within $TimeoutSeconds seconds."
}

Write-Step "Verify asset history, audit trail and preview URL"
$history = Invoke-RestMethod -Method Get -Uri "$GatewayBaseUrl/api/v1/assets/history" -Headers $headers
$historyItem = @($history.data | Where-Object { [int64]$_.job_id -eq $jobId } | Sort-Object created_at -Descending) | Select-Object -First 1
if ($null -eq $historyItem) {
  throw "Asset history did not contain job_id=$jobId."
}

$auditEvents = Invoke-RestMethod -Method Get -Uri "$GatewayBaseUrl/api/v1/audit/tasks/$jobId/events" -Headers $headers
if ([double]$historyItem.total_score -le 0) {
  throw "Scoring result is invalid: total_score=$($historyItem.total_score)"
}

if (@($auditEvents.data).Count -lt 4) {
  throw "Audit trail is incomplete: only $(@($auditEvents.data).Count) events."
}

$previewName = [System.IO.Path]::GetFileName([string]$historyItem.file_path)
$previewUrl = "$GatewayBaseUrl/files/images/$previewName"
$previewResponse = Invoke-WebRequest -Uri $previewUrl -UseBasicParsing -TimeoutSec 30
if ($previewResponse.StatusCode -ne 200) {
  throw "Preview fetch failed: $previewUrl"
}

$result = [PSCustomObject]@{
  job_id            = $jobId
  model_name        = $ModelName
  asset_id          = [int64]$historyItem.id
  file_path         = [string]$historyItem.file_path
  preview_url       = $previewUrl
  total_score       = [double]$historyItem.total_score
  audit_event_count = @($auditEvents.data).Count
  task_stage        = $detail.data.stage
  task_status       = $detail.data.status
}

Write-Step "Docker smoke test passed"
$result | ConvertTo-Json -Depth 4
