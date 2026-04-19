package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadBuildsConfigFromEnv(t *testing.T) {
	t.Setenv("APP_NAME", "auth-service")
	t.Setenv("HTTP_PORT", "8081")
	t.Setenv("MYSQL_DSN", "root:root@tcp(localhost:3306)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local")
	t.Setenv("REDIS_ADDR", "localhost:6379")
	t.Setenv("JWT_SECRET", "electric-ai-secret")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
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

func TestLoadReturnsErrorWhenJWTSecretMissing(t *testing.T) {
	t.Setenv("JWT_SECRET", "")

	_, err := Load()
	if err == nil {
		t.Fatalf("expected error when JWT_SECRET is missing")
	}
}

func TestLoadReadsDotEnvLocalFromWorkingDirectory(t *testing.T) {
	tempDir := t.TempDir()
	envFile := filepath.Join(tempDir, ".env.local")
	envContent := "APP_NAME=asset-service\nHTTP_PORT=8084\nMYSQL_DSN=root:root@tcp(127.0.0.1:13307)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local\nREDIS_ADDR=127.0.0.1:16380\nJWT_SECRET=electric-ai-secret\n"
	if err := os.WriteFile(envFile, []byte(envContent), 0o644); err != nil {
		t.Fatalf("write env file: %v", err)
	}

	restoreCwd := chdirTemp(t, tempDir)
	defer restoreCwd()
	unsetConfigEnv(t)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.AppName != "asset-service" {
		t.Fatalf("expected asset-service, got %s", cfg.AppName)
	}
	if cfg.HTTPPort != "8084" {
		t.Fatalf("expected 8084, got %s", cfg.HTTPPort)
	}
	if cfg.RedisAddr != "127.0.0.1:16380" {
		t.Fatalf("expected redis addr from env file, got %s", cfg.RedisAddr)
	}
}

func TestLoadPrefersExplicitEnvOverDotEnvLocal(t *testing.T) {
	tempDir := t.TempDir()
	envFile := filepath.Join(tempDir, ".env.local")
	envContent := "APP_NAME=asset-service\nHTTP_PORT=8084\nMYSQL_DSN=root:root@tcp(127.0.0.1:13307)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local\nREDIS_ADDR=127.0.0.1:16380\nJWT_SECRET=file-secret\n"
	if err := os.WriteFile(envFile, []byte(envContent), 0o644); err != nil {
		t.Fatalf("write env file: %v", err)
	}

	restoreCwd := chdirTemp(t, tempDir)
	defer restoreCwd()
	unsetConfigEnv(t)
	t.Setenv("HTTP_PORT", "9094")
	t.Setenv("JWT_SECRET", "override-secret")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.HTTPPort != "9094" {
		t.Fatalf("expected explicit env to win, got %s", cfg.HTTPPort)
	}
	if cfg.JWTSecret != "override-secret" {
		t.Fatalf("expected explicit jwt secret to win, got %s", cfg.JWTSecret)
	}
}

func TestLoadPrefersNearestDotEnvLocalOverParent(t *testing.T) {
	parentDir := t.TempDir()
	childDir := filepath.Join(parentDir, "services", "asset-service")
	if err := os.MkdirAll(childDir, 0o755); err != nil {
		t.Fatalf("mkdir child: %v", err)
	}

	parentEnv := "JWT_SECRET=parent-secret\nMYSQL_DSN=root:root@tcp(127.0.0.1:3307)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local\nREDIS_ADDR=127.0.0.1:6380\n"
	childEnv := "APP_NAME=asset-service\nHTTP_PORT=8084\nJWT_SECRET=child-secret\n"
	if err := os.WriteFile(filepath.Join(parentDir, ".env.local"), []byte(parentEnv), 0o644); err != nil {
		t.Fatalf("write parent env: %v", err)
	}
	if err := os.WriteFile(filepath.Join(childDir, ".env.local"), []byte(childEnv), 0o644); err != nil {
		t.Fatalf("write child env: %v", err)
	}

	restoreCwd := chdirTemp(t, childDir)
	defer restoreCwd()
	unsetConfigEnv(t)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if cfg.AppName != "asset-service" {
		t.Fatalf("expected child app name, got %s", cfg.AppName)
	}
	if cfg.HTTPPort != "8084" {
		t.Fatalf("expected child http port, got %s", cfg.HTTPPort)
	}
	if cfg.JWTSecret != "child-secret" {
		t.Fatalf("expected child jwt secret, got %s", cfg.JWTSecret)
	}
	if cfg.RedisAddr != "127.0.0.1:6380" {
		t.Fatalf("expected parent redis addr, got %s", cfg.RedisAddr)
	}
}

func chdirTemp(t *testing.T, dir string) func() {
	t.Helper()
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatalf("chdir: %v", err)
	}
	return func() {
		if err := os.Chdir(cwd); err != nil {
			t.Fatalf("restore cwd: %v", err)
		}
	}
}

func unsetConfigEnv(t *testing.T) {
	t.Helper()
	for _, key := range []string{"APP_NAME", "HTTP_PORT", "MYSQL_DSN", "REDIS_ADDR", "JWT_SECRET"} {
		if err := os.Unsetenv(key); err != nil {
			t.Fatalf("unsetenv %s: %v", key, err)
		}
	}
}
