package config

import "os"

type Config struct {
	AppName   string
	HTTPPort  string
	MySQLDSN  string
	RedisAddr string
	JWTSecret string
}

func Load() Config {
	return Config{
		AppName:   getenv("APP_NAME", "unknown-service"),
		HTTPPort:  getenv("HTTP_PORT", "8080"),
		MySQLDSN:  getenv("MYSQL_DSN", ""),
		RedisAddr: getenv("REDIS_ADDR", "localhost:6379"),
		JWTSecret: getenv("JWT_SECRET", "electric-ai-secret"),
	}
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
