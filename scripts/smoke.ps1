$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/v1/auth/login" -ContentType "application/json" -Body '{"username":"admin","password":"admin123456"}'
if (-not $login.data.access_token) {
  throw "missing access token"
}

$headers = @{ Authorization = "Bearer $($login.data.access_token)" }

$models = Invoke-RestMethod -Headers $headers -Uri "http://localhost:8080/api/v1/models"
if ($models.data.Count -lt 1) {
  throw "no active models returned"
}

$task = Invoke-RestMethod -Method Post -Headers $headers -Uri "http://localhost:8080/api/v1/tasks/generate" -ContentType "application/json" -Body '{"prompt":"A wind turbine farm at sunset","negative_prompt":"blurry","model_name":"UniPic-2"}'
if (-not $task.data.id) {
  throw "task creation failed"
}

Write-Host "Smoke test passed."
