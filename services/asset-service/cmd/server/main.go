package main

import (
	"database/sql"
	"log"

	_ "github.com/go-sql-driver/mysql"

	"electric-ai/services/asset-service/controller"
	"electric-ai/services/asset-service/repository"
	"electric-ai/services/asset-service/router"
	"electric-ai/services/asset-service/service"
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

	assetRepo := repository.NewAssetRepository(db)
	assetSvc := service.NewAssetService(assetRepo)
	assetController := controller.NewAssetController(assetSvc)

	engine := router.New(assetController)
	if err := engine.Run(":" + cfg.HTTPPort); err != nil {
		log.Fatalf("run server failed: %v", err)
	}
}
