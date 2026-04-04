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
