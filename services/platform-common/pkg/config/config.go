package config

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/joho/godotenv"
)

// Config 定义所有 Go 微服务共享的基础运行配置。
type Config struct {
	AppName   string
	HTTPPort  string
	MySQLDSN  string
	RedisAddr string
	JWTSecret string
}

// Load 会优先装载当前服务目录向上的 .env / .env.local，再读取进程环境变量。
// 这样既兼容 Docker 注入，也兼容 GoLand 本地直接运行。
func Load() (Config, error) {
	loadLocalEnvFiles()

	jwtSecret, err := getenvRequired("JWT_SECRET")
	if err != nil {
		return Config{}, err
	}

	return Config{
		AppName:   getenv("APP_NAME", "unknown-service"),
		HTTPPort:  getenv("HTTP_PORT", "8080"),
		MySQLDSN:  getenv("MYSQL_DSN", "root:root@tcp(127.0.0.1:3307)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local"),
		RedisAddr: getenv("REDIS_ADDR", "localhost:6380"),
		// TODO: 生产环境应从密钥管理系统读取 JWT_SECRET，而不是仅依赖环境变量文件。
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

// loadLocalEnvFiles 只在变量尚未显式注入时回填本地文件，避免覆盖 Docker / IDE 配置。
func loadLocalEnvFiles() {
	for _, path := range dotenvCandidates() {
		values, err := godotenv.Read(path)
		if err != nil {
			continue
		}

		for key, value := range values {
			if os.Getenv(key) == "" {
				_ = os.Setenv(key, value)
			}
		}
	}
}

// dotenvCandidates 会把工作目录向上的 .env 与 .env.local 都纳入候选，
// 让 monorepo 下的服务既能继承根配置，也能拥有自己的局部覆盖。
func dotenvCandidates() []string {
	cwd, err := os.Getwd()
	if err != nil {
		return nil
	}

	var dirs []string
	for dir := cwd; ; dir = filepath.Dir(dir) {
		dirs = append([]string{dir}, dirs...)
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
	}

	seen := make(map[string]struct{})
	var paths []string
	for _, dir := range dirs {
		for _, name := range []string{".env", ".env.local"} {
			path := filepath.Join(dir, name)
			if _, err := os.Stat(path); err != nil {
				continue
			}
			if _, ok := seen[path]; ok {
				continue
			}
			seen[path] = struct{}{}
			paths = append(paths, path)
		}
	}

	return paths
}
