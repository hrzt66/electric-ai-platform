package main

import (
	"context"
	"database/sql"
	"log"

	_ "github.com/go-sql-driver/mysql"
	"github.com/redis/go-redis/v9"

	"electric-ai/services/platform-common/pkg/config"
	"electric-ai/services/task-service/controller"
	"electric-ai/services/task-service/repository"
	"electric-ai/services/task-service/router"
	"electric-ai/services/task-service/service"
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

	rdb := redis.NewClient(&redis.Options{Addr: cfg.RedisAddr})
	defer rdb.Close()

	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("ping redis failed: %v", err)
	}

	taskRepo := repository.NewTaskRepository(db)
	taskSvc := service.NewTaskService(taskRepo, rdb)
	taskController := controller.NewTaskController(taskSvc)

	engine := router.New(taskController)
	if err := engine.Run(":" + cfg.HTTPPort); err != nil {
		log.Fatalf("run server failed: %v", err)
	}
}
