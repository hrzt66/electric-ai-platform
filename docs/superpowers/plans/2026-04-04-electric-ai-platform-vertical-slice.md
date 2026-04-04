# Electric AI Platform Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable first-phase vertical slice of the electric AI image platform: login, model registry lookup, create generate task, Redis-driven async processing, Python AI mock generation/scoring, asset persistence, audit events, and a Vite console that can submit a task and watch it complete.

**Architecture:** Use a monorepo with shared Go platform packages, six Gin microservices (`gateway`, `auth`, `model`, `task`, `asset`, `audit`), one FastAPI-based Python AI service, and one Vue 3 console. The first phase uses a mocked Python image generator/scorer so we can validate service boundaries, task orchestration, storage, and UI flow before integrating real diffusion and scoring runtimes in a subsequent plan.

**Tech Stack:** Go 1.24, Gin, GORM, go-redis, FastAPI, Pydantic, Pillow, Vue 3, Vite, TypeScript, Pinia, Element Plus, MySQL 8, Redis 7, Docker Compose, Vitest, pytest.

---

## Scope Split

The approved design spans multiple independent subsystems, so implementation should be split into sequential plans:

1. This plan: vertical slice foundation with mocked AI runtime and the critical end-to-end path.
2. Follow-on plan: replace mock generation/scoring with real Python model scripts and GPU/runtime management.
3. Follow-on plan: governance features, batch experiments, exports, and full RBAC surfaces.
4. Follow-on plan: observability hardening, alerting, performance tuning, and production deployment polish.

This plan must produce working, testable software on its own.

## File Structure

Create this monorepo layout first and keep the responsibility boundaries stable:

```text
services/
  platform-common/      shared config, logging, response, JWT, DB, Redis helpers
  gateway-service/      public API gateway and auth-aware reverse proxy
  auth-service/         login, token issue, user bootstrap
  model-service/        model registry and prompt template read APIs
  task-service/         async job creation, polling, Redis stream publish
  asset-service/        image, prompt, score persistence and query APIs
  audit-service/        operation and task event ingestion/query
python-ai-service/      FastAPI service for generate/score worker endpoints
web-console/            Vue 3 + Vite admin console
deploy/
  docker/               Dockerfiles
  mysql/init/           schema and seed SQL
  docker-compose.dev.yml
scripts/                PowerShell scripts for local dev and smoke checks
storage/                local image/output directories
```

## Task 1: Bootstrap the Workspace and Shared Go Platform Package

**Files:**
- Create: `.gitignore`
- Create: `go.work`
- Create: `services/platform-common/go.mod`
- Create: `services/platform-common/pkg/config/config.go`
- Create: `services/platform-common/pkg/config/config_test.go`
- Create: `services/platform-common/pkg/httpx/response.go`
- Create: `services/platform-common/pkg/logger/logger.go`
- Create: `services/platform-common/pkg/jwtx/jwt.go`
- Create: `README.md`

- [ ] **Step 1: Write the failing config loader test**

```go
package config

import "testing"

func TestLoadBuildsConfigFromEnv(t *testing.T) {
	t.Setenv("APP_NAME", "auth-service")
	t.Setenv("HTTP_PORT", "8081")
	t.Setenv("MYSQL_DSN", "root:root@tcp(localhost:3306)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local")
	t.Setenv("REDIS_ADDR", "localhost:6379")
	t.Setenv("JWT_SECRET", "electric-ai-secret")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}

	if cfg.AppName != "auth-service" {
		t.Fatalf("expected auth-service, got %s", cfg.AppName)
	}
	if cfg.HTTPPort != "8081" {
		t.Fatalf("expected 8081, got %s", cfg.HTTPPort)
	}
	if cfg.JWTSecret != "electric-ai-secret" {
		t.Fatalf("expected jwt secret to be loaded")
	}
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `go test ./pkg/config -v`

Expected: FAIL with `undefined: Load`

- [ ] **Step 3: Write the minimal shared platform implementation**

`services/platform-common/go.mod`

```go
module electric-ai/services/platform-common

go 1.24.0

require github.com/golang-jwt/jwt/v5 v5.2.1
```

`go.work`

```text
go 1.24.0

use (
	./services/platform-common
)
```

`services/platform-common/pkg/config/config.go`

```go
package config

import (
	"fmt"
	"os"
)

type Config struct {
	AppName   string
	HTTPPort  string
	MySQLDSN  string
	RedisAddr string
	JWTSecret string
}

func Load() (Config, error) {
	jwtSecret, err := getenvRequired("JWT_SECRET")
	if err != nil {
		return Config{}, err
	}

	return Config{
		AppName:   getenv("APP_NAME", "unknown-service"),
		HTTPPort:  getenv("HTTP_PORT", "8080"),
		MySQLDSN:  getenv("MYSQL_DSN", ""),
		RedisAddr: getenv("REDIS_ADDR", "localhost:6379"),
		JWTSecret: jwtSecret,
	}, nil
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func getenvRequired(key string) (string, error) {
	value := os.Getenv(key)
	if value == "" {
		return "", fmt.Errorf("missing required env var: %s", key)
	}
	return value, nil
}
```

`services/platform-common/pkg/httpx/response.go`

```go
package httpx

type Response[T any] struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    T      `json:"data"`
	TraceID string `json:"trace_id"`
}

func OK[T any](data T, traceID string) Response[T] {
	return Response[T]{Code: 0, Message: "success", Data: data, TraceID: traceID}
}
```

`services/platform-common/pkg/logger/logger.go`

```go
package logger

import "log"

func Info(format string, args ...any) {
	log.Printf("[INFO] "+format, args...)
}

func Error(format string, args ...any) {
	log.Printf("[ERROR] "+format, args...)
}
```

`services/platform-common/pkg/jwtx/jwt.go`

```go
package jwtx

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func Issue(secret, userID, username string, expireMinutes int) (string, error) {
	claims := jwt.MapClaims{
		"user_id":  userID,
		"username": username,
		"exp":      time.Now().Add(time.Duration(expireMinutes) * time.Minute).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secret))
}
```

- [ ] **Step 4: Run the shared package tests**

Run: `go test ./pkg/... -v`

Expected: PASS with `TestLoadBuildsConfigFromEnv`

- [ ] **Step 5: Commit**

```bash
git add .gitignore go.work README.md services/platform-common
git commit -m "feat: bootstrap shared go platform package"
```

## Task 2: Stand Up Dev Infrastructure and Baseline Schema

**Files:**
- Create: `deploy/docker-compose.dev.yml`
- Create: `deploy/mysql/init/001_schema.sql`
- Create: `deploy/mysql/init/002_seed.sql`
- Create: `scripts/verify-schema.ps1`
- Create: `scripts/dev-up.ps1`
- Create: `scripts/dev-down.ps1`

- [ ] **Step 1: Write the failing schema verification script**

`scripts/verify-schema.ps1`

```powershell
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
```

- [ ] **Step 2: Run the verification before the schema exists**

Run: `powershell -File scripts/verify-schema.ps1`

Expected: FAIL with `Missing table`

- [ ] **Step 3: Write the Docker Compose dev infra and baseline SQL**

`deploy/docker-compose.dev.yml`

```yaml
services:
  mysql:
    image: mysql:8.4
    container_name: electric-ai-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: electric_ai
    ports:
      - "3306:3306"
    volumes:
      - ./mysql/init:/docker-entrypoint-initdb.d

  redis:
    image: redis:7.2
    container_name: electric-ai-redis
    ports:
      - "6379:6379"
```

`deploy/mysql/init/001_schema.sql`

```sql
CREATE TABLE auth_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE model_registry (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(32) NOT NULL,
    service_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE model_prompt_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    template_name VARCHAR(255) NOT NULL,
    scene_type VARCHAR(64) NOT NULL,
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE task_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    payload_json JSON NOT NULL,
    result_json JSON NULL,
    error_message TEXT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE asset_images (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_id BIGINT NOT NULL,
    image_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE asset_image_prompts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    image_id BIGINT NOT NULL,
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT NULL,
    sampling_steps INT NOT NULL,
    seed BIGINT NOT NULL,
    guidance_scale DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_image_prompts_image FOREIGN KEY (image_id) REFERENCES asset_images(id) ON DELETE CASCADE
);

CREATE TABLE asset_image_scores (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    image_id BIGINT NOT NULL,
    visual_fidelity DECIMAL(5,2) NOT NULL,
    text_consistency DECIMAL(5,2) NOT NULL,
    physical_plausibility DECIMAL(5,2) NOT NULL,
    composition_aesthetics DECIMAL(5,2) NOT NULL,
    total_score DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_image_scores_image FOREIGN KEY (image_id) REFERENCES asset_images(id) ON DELETE CASCADE
);

CREATE TABLE audit_task_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_id BIGINT NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    message VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`deploy/mysql/init/002_seed.sql`

```sql
INSERT INTO auth_users (username, password_hash, display_name)
VALUES ('admin', '$2a$10$MVsC0z7o3g8X9h9O0uHkXee4g0S6g5n8J2zM6W7Wm2mM5sV2uQ9O6', '系统管理员');

INSERT INTO model_registry (model_name, model_type, service_name, status)
VALUES
('UniPic-2', 'generation', 'python-ai-service', 'active'),
('Electric-Score-v1', 'scoring', 'python-ai-service', 'active');

INSERT INTO model_prompt_templates (template_name, scene_type, positive_prompt, negative_prompt)
VALUES
('风电场基础模板', 'wind-farm', 'A modern wind turbine farm at sunset', 'blurry, deformed, low quality');
```

`scripts/dev-up.ps1`

```powershell
docker compose -f deploy/docker-compose.dev.yml up -d mysql redis
```

`scripts/dev-down.ps1`

```powershell
docker compose -f deploy/docker-compose.dev.yml down -v
```

- [ ] **Step 4: Recreate the infra and verify the schema**

Run: `powershell -File scripts/dev-down.ps1`

Run: `powershell -File scripts/dev-up.ps1`

Run: `powershell -File scripts/verify-schema.ps1`

Expected: PASS with `Schema verification passed.`

- [ ] **Step 5: Commit**

```bash
git add deploy scripts
git commit -m "feat: add dev infra and baseline schema"
```

## Task 3: Build the Auth Service Vertical Slice

**Files:**
- Create: `services/auth-service/go.mod`
- Create: `services/auth-service/cmd/server/main.go`
- Create: `services/auth-service/router/router.go`
- Create: `services/auth-service/controller/auth_controller.go`
- Create: `services/auth-service/service/auth_service.go`
- Create: `services/auth-service/service/auth_service_test.go`
- Create: `services/auth-service/repository/user_repository.go`
- Create: `services/auth-service/model/user.go`
- Create: `services/auth-service/model/dto.go`

- [ ] **Step 1: Write the failing auth service test**

```go
package service

import (
	"context"
	"testing"
)

type stubUserRepo struct {
	user *LoginUser
}

func (s *stubUserRepo) FindByUsername(_ context.Context, username string) (*LoginUser, error) {
	if s.user != nil && s.user.Username == username {
		return s.user, nil
	}
	return nil, ErrInvalidCredentials
}

func TestLoginReturnsTokenForValidUser(t *testing.T) {
	repo := &stubUserRepo{
		user: &LoginUser{
			ID:           1,
			Username:     "admin",
			DisplayName:  "系统管理员",
			PasswordHash: "$2a$10$MVsC0z7o3g8X9h9O0uHkXee4g0S6g5n8J2zM6W7Wm2mM5sV2uQ9O6",
		},
	}

	svc := NewAuthService(repo, "electric-ai-secret")
	result, err := svc.Login(context.Background(), LoginRequest{Username: "admin", Password: "admin123456"})
	if err != nil {
		t.Fatalf("expected login success, got %v", err)
	}
	if result.AccessToken == "" {
		t.Fatal("expected access token")
	}
}
```

- [ ] **Step 2: Run the auth test to verify it fails**

Run: `go test ./service -v`

Expected: FAIL with `undefined: LoginUser` or `undefined: NewAuthService`

- [ ] **Step 3: Write the minimal auth service implementation**

`services/auth-service/model/dto.go`

```go
package model

type LoginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type LoginResponse struct {
	AccessToken string `json:"access_token"`
	UserName    string `json:"user_name"`
	DisplayName string `json:"display_name"`
}
```

`services/auth-service/model/user.go`

```go
package model

type User struct {
	ID           int64
	Username     string
	DisplayName  string
	PasswordHash string
	Status       string
}
```

`services/auth-service/service/auth_service.go`

```go
package service

import (
	"context"
	"errors"

	"golang.org/x/crypto/bcrypt"

	"electric-ai/services/auth-service/model"
	"electric-ai/services/platform-common/pkg/jwtx"
)

var ErrInvalidCredentials = errors.New("invalid credentials")

type LoginUser = model.User
type LoginRequest = model.LoginRequest
type LoginResponse = model.LoginResponse

type UserRepository interface {
	FindByUsername(ctx context.Context, username string) (*LoginUser, error)
}

type AuthService struct {
	repo      UserRepository
	jwtSecret string
}

func NewAuthService(repo UserRepository, jwtSecret string) *AuthService {
	return &AuthService{repo: repo, jwtSecret: jwtSecret}
}

func (s *AuthService) Login(ctx context.Context, req LoginRequest) (LoginResponse, error) {
	user, err := s.repo.FindByUsername(ctx, req.Username)
	if err != nil {
		return LoginResponse{}, ErrInvalidCredentials
	}
	if bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)) != nil {
		return LoginResponse{}, ErrInvalidCredentials
	}
	token, err := jwtx.Issue(s.jwtSecret, "1", user.Username, 120)
	if err != nil {
		return LoginResponse{}, err
	}
	return LoginResponse{
		AccessToken: token,
		UserName:    user.Username,
		DisplayName: user.DisplayName,
	}, nil
}
```

`services/auth-service/controller/auth_controller.go`

```go
package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/auth-service/model"
	"electric-ai/services/auth-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type AuthController struct {
	svc *service.AuthService
}

func NewAuthController(svc *service.AuthService) *AuthController {
	return &AuthController{svc: svc}
}

func (c *AuthController) Login(ctx *gin.Context) {
	var req model.LoginRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{"message": err.Error()})
		return
	}

	result, err := c.svc.Login(ctx, req)
	if err != nil {
		ctx.JSON(http.StatusUnauthorized, gin.H{"message": err.Error()})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(result, "auth-login"))
}
```

- [ ] **Step 4: Run the auth tests**

Run: `go test ./service -v`

Expected: PASS with `TestLoginReturnsTokenForValidUser`

- [ ] **Step 5: Commit**

```bash
git add services/auth-service go.work
git commit -m "feat: add auth service login vertical slice"
```

## Task 4: Build the Model Service Vertical Slice

**Files:**
- Create: `services/model-service/go.mod`
- Create: `services/model-service/cmd/server/main.go`
- Create: `services/model-service/router/router.go`
- Create: `services/model-service/controller/model_controller.go`
- Create: `services/model-service/service/model_service.go`
- Create: `services/model-service/service/model_service_test.go`
- Create: `services/model-service/repository/model_repository.go`
- Create: `services/model-service/model/model.go`

- [ ] **Step 1: Write the failing model service test**

```go
package service

import (
	"context"
	"testing"
)

type stubRepo struct {
	items []RegistryModel
}

func (s *stubRepo) ListActive(ctx context.Context) ([]RegistryModel, error) {
	return s.items, nil
}

func TestListActiveModelsReturnsOnlyActiveRecords(t *testing.T) {
	repo := &stubRepo{
		items: []RegistryModel{
			{ID: 1, ModelName: "UniPic-2", ModelType: "generation", Status: "active"},
		},
	}

	svc := NewModelService(repo)
	items, err := svc.ListActive(context.Background())
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(items) != 1 || items[0].ModelName != "UniPic-2" {
		t.Fatalf("unexpected models: %+v", items)
	}
}
```

- [ ] **Step 2: Run the model test to verify it fails**

Run: `go test ./service -v`

Expected: FAIL with `undefined: RegistryModel` or `undefined: NewModelService`

- [ ] **Step 3: Write the model registry implementation**

`services/model-service/model/model.go`

```go
package model

type RegistryModel struct {
	ID          int64  `json:"id"`
	ModelName   string `json:"model_name"`
	ModelType   string `json:"model_type"`
	ServiceName string `json:"service_name"`
	Status      string `json:"status"`
}
```

`services/model-service/service/model_service.go`

```go
package service

import (
	"context"

	"electric-ai/services/model-service/model"
)

type RegistryModel = model.RegistryModel

type Repository interface {
	ListActive(ctx context.Context) ([]RegistryModel, error)
}

type ModelService struct {
	repo Repository
}

func NewModelService(repo Repository) *ModelService {
	return &ModelService{repo: repo}
}

func (s *ModelService) ListActive(ctx context.Context) ([]RegistryModel, error) {
	return s.repo.ListActive(ctx)
}
```

`services/model-service/controller/model_controller.go`

```go
package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/model-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type ModelController struct {
	svc *service.ModelService
}

func NewModelController(svc *service.ModelService) *ModelController {
	return &ModelController{svc: svc}
}

func (c *ModelController) ListActive(ctx *gin.Context) {
	items, err := c.svc.ListActive(ctx)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{"message": err.Error()})
		return
	}
	ctx.JSON(http.StatusOK, httpx.OK(items, "model-list"))
}
```

- [ ] **Step 4: Run the model service tests**

Run: `go test ./service -v`

Expected: PASS with `TestListActiveModelsReturnsOnlyActiveRecords`

- [ ] **Step 5: Commit**

```bash
git add services/model-service go.work
git commit -m "feat: add model service vertical slice"
```

## Task 5: Build the Task Service with Redis Stream Publishing

**Files:**
- Create: `services/task-service/go.mod`
- Create: `services/task-service/cmd/server/main.go`
- Create: `services/task-service/router/router.go`
- Create: `services/task-service/controller/task_controller.go`
- Create: `services/task-service/service/task_service.go`
- Create: `services/task-service/service/task_service_test.go`
- Create: `services/task-service/repository/task_repository.go`
- Create: `services/task-service/model/task.go`

- [ ] **Step 1: Write the failing task service test**

```go
package service

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

type memoryRepo struct {
	nextID int64
	items  []Job
}

func (m *memoryRepo) Create(ctx context.Context, job Job) (Job, error) {
	m.nextID++
	job.ID = m.nextID
	m.items = append(m.items, job)
	return job, nil
}

func TestCreateGenerateJobStoresJobAndPublishesToRedis(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	repo := &memoryRepo{}
	svc := NewTaskService(repo, rdb)

	job, err := svc.CreateGenerateJob(context.Background(), CreateGenerateJobInput{
		Prompt:         "A wind turbine farm at sunset",
		NegativePrompt: "blurry",
		ModelName:      "UniPic-2",
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if job.Status != "queued" {
		t.Fatalf("expected queued status, got %s", job.Status)
	}
	if mr.Exists("stream:generate:jobs") == false {
		t.Fatal("expected stream entry")
	}
}
```

- [ ] **Step 2: Run the task service test to verify it fails**

Run: `go test ./service -v`

Expected: FAIL with `undefined: Job` or `undefined: NewTaskService`

- [ ] **Step 3: Write the task service implementation**

`services/task-service/model/task.go`

```go
package model

type Job struct {
	ID          int64  `json:"id"`
	JobType     string `json:"job_type"`
	Status      string `json:"status"`
	PayloadJSON string `json:"payload_json"`
}

type CreateGenerateJobInput struct {
	Prompt         string `json:"prompt"`
	NegativePrompt string `json:"negative_prompt"`
	ModelName      string `json:"model_name"`
}
```

`services/task-service/service/task_service.go`

```go
package service

import (
	"context"
	"encoding/json"

	"github.com/redis/go-redis/v9"

	"electric-ai/services/task-service/model"
)

type Job = model.Job
type CreateGenerateJobInput = model.CreateGenerateJobInput

type Repository interface {
	Create(ctx context.Context, job Job) (Job, error)
}

type TaskService struct {
	repo Repository
	rdb  *redis.Client
}

func NewTaskService(repo Repository, rdb *redis.Client) *TaskService {
	return &TaskService{repo: repo, rdb: rdb}
}

func (s *TaskService) CreateGenerateJob(ctx context.Context, input CreateGenerateJobInput) (Job, error) {
	payload, err := json.Marshal(input)
	if err != nil {
		return Job{}, err
	}

	job, err := s.repo.Create(ctx, Job{
		JobType:     "generate",
		Status:      "queued",
		PayloadJSON: string(payload),
	})
	if err != nil {
		return Job{}, err
	}

	if err := s.rdb.XAdd(ctx, &redis.XAddArgs{
		Stream: "stream:generate:jobs",
		Values: map[string]any{
			"job_id":  job.ID,
			"payload": string(payload),
		},
	}).Err(); err != nil {
		return Job{}, err
	}

	return job, nil
}
```

- [ ] **Step 4: Run the task service tests**

Run: `go test ./service -v`

Expected: PASS with `TestCreateGenerateJobStoresJobAndPublishesToRedis`

- [ ] **Step 5: Commit**

```bash
git add services/task-service go.work
git commit -m "feat: add task service job enqueue flow"
```

## Task 6: Build the Python AI Service Mock Generate and Score Endpoints

**Files:**
- Create: `python-ai-service/requirements.txt`
- Create: `python-ai-service/app/main.py`
- Create: `python-ai-service/app/schemas/jobs.py`
- Create: `python-ai-service/app/services/mock_generator.py`
- Create: `python-ai-service/app/services/mock_scorer.py`
- Create: `python-ai-service/tests/test_main.py`
- Create: `storage/images/.gitkeep`

- [ ] **Step 1: Write the failing Python API test**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_returns_file_path_and_scores():
    response = client.post(
        "/internal/generate",
        json={
            "job_id": 1,
            "prompt": "A wind turbine farm at sunset",
            "negative_prompt": "blurry",
            "model_name": "UniPic-2",
            "seed": 42,
            "steps": 20,
            "guidance_scale": 7.5,
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["file_path"].endswith(".png")
    assert payload["scores"]["visual_fidelity"] >= 0
```

- [ ] **Step 2: Run the Python test to verify it fails**

Run: `pytest tests/test_main.py -q`

Expected: FAIL with `ModuleNotFoundError` or missing `/internal/generate`

- [ ] **Step 3: Write the mock generate and score implementation**

`python-ai-service/requirements.txt`

```text
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2
pillow==10.4.0
pytest==8.3.3
httpx==0.27.2
```

`python-ai-service/app/schemas/jobs.py`

```python
from pydantic import BaseModel


class GenerateRequest(BaseModel):
    job_id: int
    prompt: str
    negative_prompt: str
    model_name: str
    seed: int
    steps: int
    guidance_scale: float


class ScoreBundle(BaseModel):
    visual_fidelity: float
    text_consistency: float
    physical_plausibility: float
    composition_aesthetics: float
    total_score: float
```

`python-ai-service/app/services/mock_scorer.py`

```python
import hashlib


def score_from_prompt(prompt: str) -> dict:
    digest = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8], 16)
    visual = 60 + digest % 20
    text = 65 + digest % 15
    physical = 62 + digest % 18
    aesthetics = 58 + digest % 22
    total = round(visual * 0.25 + text * 0.30 + physical * 0.30 + aesthetics * 0.15, 2)
    return {
        "visual_fidelity": float(visual),
        "text_consistency": float(text),
        "physical_plausibility": float(physical),
        "composition_aesthetics": float(aesthetics),
        "total_score": total,
    }
```

`python-ai-service/app/services/mock_generator.py`

```python
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.mock_scorer import score_from_prompt


def generate_placeholder(job_id: int, prompt: str) -> dict:
    output_dir = Path("../storage/images").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"job-{job_id}.png"

    image = Image.new("RGB", (1024, 768), color=(26, 72, 124))
    draw = ImageDraw.Draw(image)
    draw.text((40, 60), prompt[:80], fill=(255, 255, 255))
    image.save(output_path)

    return {
        "file_path": str(output_path),
        "scores": score_from_prompt(prompt),
    }
```

`python-ai-service/app/main.py`

```python
from fastapi import FastAPI

from app.schemas.jobs import GenerateRequest
from app.services.mock_generator import generate_placeholder

app = FastAPI(title="python-ai-service")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/internal/generate")
def generate(request: GenerateRequest) -> dict:
    result = generate_placeholder(request.job_id, request.prompt)
    return {"code": 0, "message": "success", "data": result, "trace_id": f"job-{request.job_id}"}
```

- [ ] **Step 4: Run the Python tests**

Run: `pytest tests/test_main.py -q`

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add python-ai-service storage/images/.gitkeep
git commit -m "feat: add python ai mock generate and score service"
```

## Task 7: Build the Asset Service Persistence Slice

**Files:**
- Create: `services/asset-service/go.mod`
- Create: `services/asset-service/cmd/server/main.go`
- Create: `services/asset-service/router/router.go`
- Create: `services/asset-service/controller/asset_controller.go`
- Create: `services/asset-service/service/asset_service.go`
- Create: `services/asset-service/service/asset_service_test.go`
- Create: `services/asset-service/repository/asset_repository.go`
- Create: `services/asset-service/model/asset.go`

- [ ] **Step 1: Write the failing asset service test**

```go
package service

import (
	"context"
	"testing"
)

type memoryAssetRepo struct {
	images []Image
}

func (m *memoryAssetRepo) SaveResult(ctx context.Context, image Image, prompt Prompt, score Score) (Image, error) {
	image.ID = int64(len(m.images) + 1)
	m.images = append(m.images, image)
	return image, nil
}

func TestSaveGenerateResultReturnsPersistedImage(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	image, err := svc.SaveGenerateResult(context.Background(), SaveGenerateResultInput{
		JobID:                  1,
		ImageName:              "job-1.png",
		FilePath:               "storage/images/job-1.png",
		ModelName:              "UniPic-2",
		PositivePrompt:         "A wind turbine farm at sunset",
		NegativePrompt:         "blurry",
		SamplingSteps:          20,
		Seed:                   42,
		GuidanceScale:          7.5,
		VisualFidelity:         75,
		TextConsistency:        78,
		PhysicalPlausibility:   76,
		CompositionAesthetics:  73,
		TotalScore:             75.7,
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if image.ID == 0 {
		t.Fatal("expected generated image id")
	}
}
```

- [ ] **Step 2: Run the asset service test to verify it fails**

Run: `go test ./service -v`

Expected: FAIL with `undefined: Image` or `undefined: NewAssetService`

- [ ] **Step 3: Write the asset service implementation**

`services/asset-service/model/asset.go`

```go
package model

type Image struct {
	ID        int64  `json:"id"`
	JobID     int64  `json:"job_id"`
	ImageName string `json:"image_name"`
	FilePath  string `json:"file_path"`
	ModelName string `json:"model_name"`
	Status    string `json:"status"`
}

type Prompt struct {
	PositivePrompt string
	NegativePrompt string
	SamplingSteps  int
	Seed           int64
	GuidanceScale  float64
}

type Score struct {
	VisualFidelity        float64
	TextConsistency       float64
	PhysicalPlausibility  float64
	CompositionAesthetics float64
	TotalScore            float64
}

type SaveGenerateResultInput struct {
	JobID                 int64
	ImageName             string
	FilePath              string
	ModelName             string
	PositivePrompt        string
	NegativePrompt        string
	SamplingSteps         int
	Seed                  int64
	GuidanceScale         float64
	VisualFidelity        float64
	TextConsistency       float64
	PhysicalPlausibility  float64
	CompositionAesthetics float64
	TotalScore            float64
}
```

`services/asset-service/service/asset_service.go`

```go
package service

import (
	"context"

	"electric-ai/services/asset-service/model"
)

type Image = model.Image
type Prompt = model.Prompt
type Score = model.Score
type SaveGenerateResultInput = model.SaveGenerateResultInput

type Repository interface {
	SaveResult(ctx context.Context, image Image, prompt Prompt, score Score) (Image, error)
}

type AssetService struct {
	repo Repository
}

func NewAssetService(repo Repository) *AssetService {
	return &AssetService{repo: repo}
}

func (s *AssetService) SaveGenerateResult(ctx context.Context, input SaveGenerateResultInput) (Image, error) {
	return s.repo.SaveResult(
		ctx,
		Image{
			JobID:     input.JobID,
			ImageName: input.ImageName,
			FilePath:  input.FilePath,
			ModelName: input.ModelName,
			Status:    "scored",
		},
		Prompt{
			PositivePrompt: input.PositivePrompt,
			NegativePrompt: input.NegativePrompt,
			SamplingSteps:  input.SamplingSteps,
			Seed:           input.Seed,
			GuidanceScale:  input.GuidanceScale,
		},
		Score{
			VisualFidelity:        input.VisualFidelity,
			TextConsistency:       input.TextConsistency,
			PhysicalPlausibility:  input.PhysicalPlausibility,
			CompositionAesthetics: input.CompositionAesthetics,
			TotalScore:            input.TotalScore,
		},
	)
}
```

- [ ] **Step 4: Run the asset service tests**

Run: `go test ./service -v`

Expected: PASS with `TestSaveGenerateResultReturnsPersistedImage`

- [ ] **Step 5: Commit**

```bash
git add services/asset-service go.work
git commit -m "feat: add asset service persistence slice"
```

## Task 8: Build the Audit Service Event Ingestion Slice

**Files:**
- Create: `services/audit-service/go.mod`
- Create: `services/audit-service/cmd/server/main.go`
- Create: `services/audit-service/router/router.go`
- Create: `services/audit-service/controller/audit_controller.go`
- Create: `services/audit-service/service/audit_service.go`
- Create: `services/audit-service/service/audit_service_test.go`
- Create: `services/audit-service/repository/audit_repository.go`
- Create: `services/audit-service/model/event.go`

- [ ] **Step 1: Write the failing audit service test**

```go
package service

import (
	"context"
	"testing"
)

type memoryEventRepo struct {
	items []TaskEvent
}

func (m *memoryEventRepo) Append(ctx context.Context, item TaskEvent) error {
	m.items = append(m.items, item)
	return nil
}

func TestRecordTaskEventAppendsAuditEvent(t *testing.T) {
	repo := &memoryEventRepo{}
	svc := NewAuditService(repo)

	err := svc.RecordTaskEvent(context.Background(), 7, "generate.completed", "mock image saved")
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(repo.items) != 1 || repo.items[0].JobID != 7 {
		t.Fatalf("unexpected events: %+v", repo.items)
	}
}
```

- [ ] **Step 2: Run the audit service test to verify it fails**

Run: `go test ./service -v`

Expected: FAIL with `undefined: TaskEvent` or `undefined: NewAuditService`

- [ ] **Step 3: Write the audit service implementation**

`services/audit-service/model/event.go`

```go
package model

type TaskEvent struct {
	JobID     int64  `json:"job_id"`
	EventType string `json:"event_type"`
	Message   string `json:"message"`
}
```

`services/audit-service/service/audit_service.go`

```go
package service

import (
	"context"

	"electric-ai/services/audit-service/model"
)

type TaskEvent = model.TaskEvent

type Repository interface {
	Append(ctx context.Context, item TaskEvent) error
}

type AuditService struct {
	repo Repository
}

func NewAuditService(repo Repository) *AuditService {
	return &AuditService{repo: repo}
}

func (s *AuditService) RecordTaskEvent(ctx context.Context, jobID int64, eventType, message string) error {
	return s.repo.Append(ctx, TaskEvent{
		JobID:     jobID,
		EventType: eventType,
		Message:   message,
	})
}
```

- [ ] **Step 4: Run the audit service tests**

Run: `go test ./service -v`

Expected: PASS with `TestRecordTaskEventAppendsAuditEvent`

- [ ] **Step 5: Commit**

```bash
git add services/audit-service go.work
git commit -m "feat: add audit event ingestion slice"
```

## Task 9: Build the Gateway Service Route Aggregation Slice

**Files:**
- Create: `services/gateway-service/go.mod`
- Create: `services/gateway-service/cmd/server/main.go`
- Create: `services/gateway-service/router/router.go`
- Create: `services/gateway-service/middleware/auth.go`
- Create: `services/gateway-service/service/proxy_service.go`
- Create: `services/gateway-service/service/proxy_service_test.go`

- [ ] **Step 1: Write the failing gateway proxy test**

```go
package service

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestProxyForwardsRequestToUpstream(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = io.WriteString(w, `{"ok":true}`)
	}))
	defer upstream.Close()

	proxy := NewReverseProxy(upstream.URL)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)

	proxy.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}
```

- [ ] **Step 2: Run the gateway test to verify it fails**

Run: `go test ./service -v`

Expected: FAIL with `undefined: NewReverseProxy`

- [ ] **Step 3: Write the minimal gateway proxy implementation**

`services/gateway-service/service/proxy_service.go`

```go
package service

import (
	"net/http/httputil"
	"net/url"
)

func NewReverseProxy(target string) *httputil.ReverseProxy {
	parsed, _ := url.Parse(target)
	return httputil.NewSingleHostReverseProxy(parsed)
}
```

`services/gateway-service/middleware/auth.go`

```go
package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

func RequireBearer() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		if strings.TrimSpace(ctx.GetHeader("Authorization")) == "" {
			ctx.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "missing authorization"})
			return
		}
		ctx.Next()
	}
}
```

`services/gateway-service/router/router.go`

```go
package router

import (
	"net/http/httputil"

	"github.com/gin-gonic/gin"

	"electric-ai/services/gateway-service/middleware"
)

type Upstreams struct {
	Auth  *httputil.ReverseProxy
	Model *httputil.ReverseProxy
	Task  *httputil.ReverseProxy
}

func New(upstreams Upstreams) *gin.Engine {
	r := gin.Default()
	r.GET("/health", func(ctx *gin.Context) { ctx.JSON(200, gin.H{"status": "ok"}) })

	r.Any("/api/v1/auth/*path", gin.WrapH(upstreams.Auth))

	secured := r.Group("/")
	secured.Use(middleware.RequireBearer())
	secured.Any("/api/v1/models/*path", gin.WrapH(upstreams.Model))
	secured.Any("/api/v1/tasks/*path", gin.WrapH(upstreams.Task))
	return r
}
```

- [ ] **Step 4: Run the gateway tests**

Run: `go test ./service -v`

Expected: PASS with `TestProxyForwardsRequestToUpstream`

- [ ] **Step 5: Commit**

```bash
git add services/gateway-service go.work
git commit -m "feat: add gateway reverse proxy slice"
```

## Task 10: Build the Web Console Vertical Slice

**Files:**
- Create: `web-console/package.json`
- Create: `web-console/vite.config.ts`
- Create: `web-console/src/main.ts`
- Create: `web-console/src/router/index.ts`
- Create: `web-console/src/stores/auth.ts`
- Create: `web-console/src/stores/auth.spec.ts`
- Create: `web-console/src/api/http.ts`
- Create: `web-console/src/views/LoginView.vue`
- Create: `web-console/src/views/DashboardView.vue`
- Create: `web-console/src/views/GenerateView.vue`

- [ ] **Step 1: Write the failing auth store test**

```ts
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'

import { useAuthStore } from './auth'

describe('auth store', () => {
  it('stores the access token after login success', async () => {
    setActivePinia(createPinia())
    const store = useAuthStore()

    store.setSession({
      accessToken: 'token-123',
      userName: 'admin',
      displayName: '系统管理员',
    })

    expect(store.accessToken).toBe('token-123')
    expect(store.displayName).toBe('系统管理员')
  })
})
```

- [ ] **Step 2: Run the web console test to verify it fails**

Run: `npm run test -- --runInBand`

Expected: FAIL with `Cannot find module './auth'`

- [ ] **Step 3: Write the minimal console implementation**

`web-console/package.json`

```json
{
  "name": "web-console",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest"
  },
  "dependencies": {
    "axios": "^1.7.7",
    "element-plus": "^2.8.4",
    "pinia": "^2.2.4",
    "vue": "^3.5.10",
    "vue-router": "^4.4.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.4",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vitest": "^2.1.2"
  }
}
```

`web-console/src/stores/auth.ts`

```ts
import { defineStore } from 'pinia'

type SessionPayload = {
  accessToken: string
  userName: string
  displayName: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '',
    userName: '',
    displayName: '',
  }),
  actions: {
    setSession(payload: SessionPayload) {
      this.accessToken = payload.accessToken
      this.userName = payload.userName
      this.displayName = payload.displayName
    },
    clearSession() {
      this.accessToken = ''
      this.userName = ''
      this.displayName = ''
    },
  },
})
```

`web-console/src/api/http.ts`

```ts
import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})
```

`web-console/src/views/LoginView.vue`

```vue
<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const form = reactive({ username: 'admin', password: 'admin123456' })

async function submit() {
  const { data } = await http.post('/auth/login', form)
  authStore.setSession({
    accessToken: data.data.access_token,
    userName: data.data.user_name,
    displayName: data.data.display_name,
  })
  router.push('/generate')
}
</script>

<template>
  <el-card class="login-card">
    <el-form @submit.prevent="submit">
      <el-form-item label="账号"><el-input v-model="form.username" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="form.password" type="password" /></el-form-item>
      <el-button type="primary" @click="submit">登录</el-button>
    </el-form>
  </el-card>
</template>
```

`web-console/src/views/GenerateView.vue`

```vue
<script setup lang="ts">
import { reactive, ref } from 'vue'

import { http } from '../api/http'

const form = reactive({
  prompt: 'A wind turbine farm at sunset',
  negative_prompt: 'blurry',
  model_name: 'UniPic-2',
})

const currentJobId = ref<number | null>(null)

async function submit() {
  const { data } = await http.post('/tasks/generate', form)
  currentJobId.value = data.data.id
}
</script>

<template>
  <div class="page">
    <el-card>
      <el-form @submit.prevent="submit">
        <el-form-item label="Prompt"><el-input v-model="form.prompt" type="textarea" /></el-form-item>
        <el-form-item label="Negative Prompt"><el-input v-model="form.negative_prompt" /></el-form-item>
        <el-form-item label="Model"><el-input v-model="form.model_name" /></el-form-item>
        <el-button type="primary" @click="submit">提交生成任务</el-button>
      </el-form>
      <p v-if="currentJobId">当前任务 ID: {{ currentJobId }}</p>
    </el-card>
  </div>
</template>
```

- [ ] **Step 4: Run the web console tests and build**

Run: `npm install`

Run: `npm run test -- --runInBand`

Run: `npm run build`

Expected: PASS and Vite build completes

- [ ] **Step 5: Commit**

```bash
git add web-console
git commit -m "feat: add web console vertical slice"
```

## Task 11: Wire the Full Stack Together with Docker and Smoke Tests

**Files:**
- Create: `deploy/docker/gateway-service.Dockerfile`
- Create: `deploy/docker/auth-service.Dockerfile`
- Create: `deploy/docker/model-service.Dockerfile`
- Create: `deploy/docker/task-service.Dockerfile`
- Create: `deploy/docker/asset-service.Dockerfile`
- Create: `deploy/docker/audit-service.Dockerfile`
- Create: `deploy/docker/python-ai-service.Dockerfile`
- Create: `deploy/docker/web-console.Dockerfile`
- Modify: `deploy/docker-compose.dev.yml`
- Create: `scripts/smoke.ps1`

- [ ] **Step 1: Write the failing smoke script**

`scripts/smoke.ps1`

```powershell
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
```

- [ ] **Step 2: Run the smoke script before the stack is wired**

Run: `powershell -File scripts/smoke.ps1`

Expected: FAIL with connection refused or missing route

- [ ] **Step 3: Add Dockerfiles and complete Docker Compose**

`deploy/docker/auth-service.Dockerfile`

```dockerfile
FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/auth-service
RUN go build -o /out/auth-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/auth-service /srv/auth-service
CMD ["/srv/auth-service"]
```

`deploy/docker/python-ai-service.Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY python-ai-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY python-ai-service /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
```

`deploy/docker/web-console.Dockerfile`

```dockerfile
FROM node:20 AS build
WORKDIR /app
COPY web-console/package*.json ./
RUN npm install
COPY web-console /app
RUN npm run build

FROM nginx:1.27
COPY --from=build /app/dist /usr/share/nginx/html
```

`deploy/docker-compose.dev.yml`

```yaml
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: electric_ai
    ports: ["3306:3306"]
    volumes:
      - ./mysql/init:/docker-entrypoint-initdb.d

  redis:
    image: redis:7.2
    ports: ["6379:6379"]

  python-ai-service:
    build:
      context: ..
      dockerfile: deploy/docker/python-ai-service.Dockerfile
    ports: ["8090:8090"]
    volumes:
      - ../storage:/storage

  auth-service:
    build:
      context: ..
      dockerfile: deploy/docker/auth-service.Dockerfile
    environment:
      APP_NAME: auth-service
      HTTP_PORT: 8081
      MYSQL_DSN: root:root@tcp(mysql:3306)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local
      JWT_SECRET: ${JWT_SECRET}
    depends_on: [mysql]
    ports: ["8081:8081"]
```

- [ ] **Step 4: Start the stack and run the smoke test**

Run: `docker compose -f deploy/docker-compose.dev.yml up --build -d`

Run: `powershell -File scripts/smoke.ps1`

Expected: PASS with `Smoke test passed.`

- [ ] **Step 5: Commit**

```bash
git add deploy scripts
git commit -m "feat: wire vertical slice stack with docker smoke test"
```

## Self-Review Checklist

- Spec coverage: this plan covers the first independent subsystem from the design, namely the runnable vertical slice from login to async generation/scoring result display.
- Placeholder scan: implementation notes must stay concrete, fully specified, and free of unfinished marker text.
- Type consistency:
  - Keep `job_id`, `model_name`, `positive_prompt`, and score field names consistent across Go services, Python API, SQL schema, and Vue client.
  - Keep task status values fixed as `queued`, `running`, `success`, `failed`, `cancelled`, `timeout`.
  - Keep score fields fixed as `visual_fidelity`, `text_consistency`, `physical_plausibility`, `composition_aesthetics`, `total_score`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-04-electric-ai-platform-vertical-slice.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
