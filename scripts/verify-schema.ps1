param(
  [string]$ComposeFile = "deploy/docker-compose.dev.yml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExpectedAdminHash = '$2b$10$ydMkvQ83zoqHxjJmCcviaupmIqse4rfj3k2eujOWeQgitZoSil05a'

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

function Invoke-ComposeQuery {
  param(
    [string]$ComposeFilePath,
    [string]$Query
  )

  $result = & docker compose -f $ComposeFilePath exec -T -e MYSQL_PWD=root mysql mysql -uroot electric_ai -Nse $Query
  if ($LASTEXITCODE -ne 0) {
    throw "MySQL query failed: $Query"
  }

  return "$($result | Select-Object -First 1)".Trim()
}

function Assert-Equals {
  param(
    [string]$Actual,
    [string]$Expected,
    [string]$Description
  )

  if ($Actual -ne $Expected) {
    throw "$Description expected '$Expected' but got '$Actual'."
  }
}

try {
  $composeFilePath = Resolve-ComposeFilePath -ComposeFile $ComposeFile

  $tables = @(
    "auth_users",
    "model_registry",
    "model_prompt_templates",
    "task_jobs",
    "asset_images",
    "asset_image_prompts",
    "asset_image_scores",
    "audit_task_events"
  )

  foreach ($table in $tables) {
    $tableCount = Invoke-ComposeQuery -ComposeFilePath $composeFilePath -Query "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'electric_ai' AND TABLE_NAME = '$table';"
    Assert-Equals -Actual $tableCount -Expected "1" -Description "Table check for $table"
  }

  $seedChecks = @(
    @{
      Description = "Seeded admin user"
      Query = "SELECT COUNT(*) FROM auth_users WHERE username = 'admin' AND password_hash = '$ExpectedAdminHash' AND status = 'active';"
      Expected = "1"
    },
    @{
      Description = "Generation model seed"
      Query = "SELECT COUNT(*) FROM model_registry WHERE model_name = 'UniPic-2' AND model_type = 'generation' AND service_name = 'python-ai-service' AND status = 'active';"
      Expected = "1"
    },
    @{
      Description = "Scoring model seed"
      Query = "SELECT COUNT(*) FROM model_registry WHERE model_name = 'Electric-Score-v1' AND model_type = 'scoring' AND service_name = 'python-ai-service' AND status = 'active';"
      Expected = "1"
    },
    @{
      Description = "Prompt template seed"
      Query = "SELECT COUNT(*) FROM model_prompt_templates WHERE template_name = 'Wind Farm Baseline' AND scene_type = 'wind-farm';"
      Expected = "1"
    }
  )

  foreach ($check in $seedChecks) {
    $result = Invoke-ComposeQuery -ComposeFilePath $composeFilePath -Query $check.Query
    Assert-Equals -Actual $result -Expected $check.Expected -Description $check.Description
  }

  $constraintChecks = @(
    @{
      Description = "asset_image_prompts.image_id foreign key"
      Query = "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = 'electric_ai' AND TABLE_NAME = 'asset_image_prompts' AND CONSTRAINT_NAME = 'fk_asset_image_prompts_image' AND CONSTRAINT_TYPE = 'FOREIGN KEY';"
      Expected = "1"
    },
    @{
      Description = "asset_image_scores.image_id foreign key"
      Query = "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = 'electric_ai' AND TABLE_NAME = 'asset_image_scores' AND CONSTRAINT_NAME = 'fk_asset_image_scores_image' AND CONSTRAINT_TYPE = 'FOREIGN KEY';"
      Expected = "1"
    },
    @{
      Description = "asset_images.job_id foreign key"
      Query = "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = 'electric_ai' AND TABLE_NAME = 'asset_images' AND CONSTRAINT_NAME = 'fk_asset_images_job' AND CONSTRAINT_TYPE = 'FOREIGN KEY';"
      Expected = "1"
    },
    @{
      Description = "audit_task_events.job_id foreign key"
      Query = "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = 'electric_ai' AND TABLE_NAME = 'audit_task_events' AND CONSTRAINT_NAME = 'fk_audit_task_events_job' AND CONSTRAINT_TYPE = 'FOREIGN KEY';"
      Expected = "1"
    },
    @{
      Description = "asset_images.job_id index"
      Query = "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = 'electric_ai' AND TABLE_NAME = 'asset_images' AND INDEX_NAME = 'idx_asset_images_job_id';"
      Expected = "1"
    },
    @{
      Description = "audit_task_events.job_id index"
      Query = "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = 'electric_ai' AND TABLE_NAME = 'audit_task_events' AND INDEX_NAME = 'idx_audit_task_events_job_id';"
      Expected = "1"
    }
  )

  foreach ($check in $constraintChecks) {
    $result = Invoke-ComposeQuery -ComposeFilePath $composeFilePath -Query $check.Query
    Assert-Equals -Actual $result -Expected $check.Expected -Description $check.Description
  }

  Write-Host "Schema verification passed."
} catch {
  Write-Error $_
  exit 1
}
