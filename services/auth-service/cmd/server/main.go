package main

import (
	"database/sql"
	"log"

	_ "github.com/go-sql-driver/mysql"

	"electric-ai/services/auth-service/controller"
	"electric-ai/services/auth-service/repository"
	"electric-ai/services/auth-service/router"
	"electric-ai/services/auth-service/service"
	"electric-ai/services/platform-common/pkg/config"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}

	db, err := sql.Open("mysql", cfg.MySQLDSN)
	if err != nil {
		log.Fatalf("open mysql failed: %v", err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		log.Fatalf("ping mysql failed: %v", err)
	}

	userRepo := repository.NewUserRepository(db)
	authSvc := service.NewAuthService(userRepo, cfg.JWTSecret)
	authController := controller.NewAuthController(authSvc)

	engine := router.New(authController)
	if err := engine.Run(":" + cfg.HTTPPort); err != nil {
		log.Fatalf("run server failed: %v", err)
	}
}
