param(
  [string]$ComposeFile = "deploy/docker-compose.dev.yml"
)

$tables = @(
  "auth_users",
  "model_registry",
  "task_jobs",
  "asset_images",
  "audit_task_events"
)

foreach ($table in $tables) {
  $result = docker compose -f $ComposeFile exec -T mysql mysql -uroot -proot electric_ai -Nse "SHOW TABLES LIKE '$table';"
  if ($result -ne $table) {
    Write-Error "Missing table: $table"
    exit 1
  }
}

Write-Host "Schema verification passed."
