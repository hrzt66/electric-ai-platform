package repository

import (
	"context"
	"database/sql"
	"errors"
	"os"
	"path/filepath"
	"sync"

	mysqlDriver "github.com/go-sql-driver/mysql"

	"electric-ai/services/model-service/model"
)

// ModelRepository 负责模型注册表的迁移、种子初始化和查询。
type ModelRepository struct {
	db         *sql.DB
	schemaOnce sync.Once
	schemaErr  error
}

// NewModelRepository 创建模型仓储实例。
func NewModelRepository(db *sql.DB) *ModelRepository {
	return &ModelRepository{db: db}
}

// modelSchemaStatements 返回模型注册表所需的建表与升级 SQL。
func modelSchemaStatements() []string {
	return []string{
		`
CREATE TABLE IF NOT EXISTS model_registry (
	id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	model_name VARCHAR(128) NOT NULL,
	display_name VARCHAR(255) NOT NULL,
	model_type VARCHAR(64) NOT NULL,
	service_name VARCHAR(128) NOT NULL,
	status VARCHAR(32) NOT NULL,
	description TEXT,
	default_positive_prompt TEXT,
	default_negative_prompt TEXT,
	local_path TEXT,
	UNIQUE KEY uk_model_registry_model_name (model_name)
)
`,
		`ALTER TABLE model_registry MODIFY COLUMN model_name VARCHAR(128) NOT NULL`,
		`ALTER TABLE model_registry ADD COLUMN display_name VARCHAR(255) NOT NULL DEFAULT '' AFTER model_name`,
		`ALTER TABLE model_registry MODIFY COLUMN model_type VARCHAR(64) NOT NULL`,
		`ALTER TABLE model_registry ADD COLUMN description TEXT NULL AFTER status`,
		`ALTER TABLE model_registry ADD COLUMN default_positive_prompt TEXT NULL AFTER description`,
		`ALTER TABLE model_registry ADD COLUMN default_negative_prompt TEXT NULL AFTER default_positive_prompt`,
		`ALTER TABLE model_registry ADD COLUMN local_path TEXT NULL AFTER default_negative_prompt`,
		`UPDATE model_registry SET display_name = model_name WHERE display_name = ''`,
		`
DELETE target
FROM model_registry AS target
INNER JOIN model_registry AS keeper
	ON target.model_name = keeper.model_name
	AND target.id > keeper.id
`,
		`ALTER TABLE model_registry ADD UNIQUE INDEX uk_model_registry_model_name (model_name)`,
	}
}

func runtimePath(parts ...string) string {
	root := os.Getenv("ELECTRIC_AI_RUNTIME_ROOT")
	if root == "" {
		root = "model"
	}
	items := append([]string{root}, parts...)
	return filepath.Join(items...)
}

// ensureSchema 确保模型表结构和基础种子数据存在。
func (r *ModelRepository) ensureSchema(ctx context.Context) error {
	r.schemaOnce.Do(func() {
		for _, statement := range modelSchemaStatements() {
			if _, r.schemaErr = r.db.ExecContext(ctx, statement); r.schemaErr != nil {
				if isIgnorableMigrationError(r.schemaErr) {
					r.schemaErr = nil
					continue
				}
				return
			}
		}

		seeds := []model.RegistryModel{
			{
				ModelName:             "sd15-electric",
				DisplayName:           "Stable Diffusion 1.5 Electric",
				ModelType:             "generation",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "SD1.5 baseline generation runtime for electric scenes",
				DefaultPositivePrompt: "500kV substation, industrial realism, detailed power equipment",
				DefaultNegativePrompt: "blurry, low quality, disconnected wires, deformed insulators",
				LocalPath:             runtimePath("generation", "sd15-electric"),
			},
			{
				ModelName:             "sd15-electric-specialized",
				DisplayName:           "Stable Diffusion 1.5 Electric Specialized",
				ModelType:             "generation",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "Electric-domain specialized SD1.5 deployment model",
				DefaultPositivePrompt: "500kV substation, realistic industrial equipment, clear wiring, detailed steel structures",
				DefaultNegativePrompt: "cartoon, toy-like, disconnected wires, impossible geometry, blurry",
				LocalPath:             runtimePath("generation", "sd15-electric-specialized"),
			},
			{
				ModelName:             "ssd1b-electric",
				DisplayName:           "SSD-1B Electric",
				ModelType:             "generation",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "SSD-1B SDXL distilled runtime tuned for lower-memory local generation",
				DefaultPositivePrompt: "wind turbines on grassland, modern wind power station, tall white turbine, clear sky, sunlight, realistic, clean composition, high detail, cinematic lighting",
				DefaultNegativePrompt: "blurry, low quality, artifact, deformed geometry",
				LocalPath:             runtimePath("generation", "ssd1b-electric"),
			},
			{
				ModelName:             "unipic2-kontext",
				DisplayName:           "UniPic2 Kontext",
				ModelType:             "generation",
				ServiceName:           "python-ai-service",
				Status:                "experimental",
				Description:           "Advanced electric scene generation runtime",
				DefaultPositivePrompt: "inspection robot, transformer yard, contextual electric environment",
				DefaultNegativePrompt: "artifact, low detail, unrealistic scale",
				LocalPath:             runtimePath("generation", "unipic2-kontext"),
			},
			{
				ModelName:             "electric-score-v1",
				DisplayName:           "Electric Score V1 (Legacy)",
				ModelType:             "scoring",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "Legacy four-dimension scorer built from ImageReward, CLIP-IQA and aesthetic predictor",
				DefaultPositivePrompt: "legacy electric scoring runtime",
				DefaultNegativePrompt: "",
				LocalPath:             runtimePath("scoring", "electric-score-v1"),
			},
			{
				ModelName:             "electric-score-v2",
				DisplayName:           "Electric Score V2 (Electric Domain)",
				ModelType:             "scoring",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "Retrained lightweight four-dimension scorer for electric scenes",
				DefaultPositivePrompt: "electric-domain scoring runtime",
				DefaultNegativePrompt: "",
				LocalPath:             runtimePath("scoring", "electric-score-v2"),
			},
			{
				ModelName:             "image-reward",
				DisplayName:           "ImageReward",
				ModelType:             "scoring",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "Text-image alignment scoring runtime",
				DefaultPositivePrompt: "alignment scorer",
				DefaultNegativePrompt: "",
				LocalPath:             runtimePath("scoring", "image-reward"),
			},
			{
				ModelName:             "aesthetic-predictor",
				DisplayName:           "Aesthetic Predictor",
				ModelType:             "scoring",
				ServiceName:           "python-ai-service",
				Status:                "available",
				Description:           "Aesthetic and composition scoring runtime",
				DefaultPositivePrompt: "aesthetic scorer",
				DefaultNegativePrompt: "",
				LocalPath:             runtimePath("scoring", "aesthetic-predictor"),
			},
		}

		for _, seed := range seeds {
			if _, r.schemaErr = r.db.ExecContext(ctx, `
INSERT INTO model_registry (model_name, display_name, model_type, service_name, status, description, default_positive_prompt, default_negative_prompt, local_path)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
	display_name = VALUES(display_name),
	model_type = VALUES(model_type),
	service_name = VALUES(service_name),
	status = VALUES(status),
	description = VALUES(description),
	default_positive_prompt = VALUES(default_positive_prompt),
	default_negative_prompt = VALUES(default_negative_prompt),
	local_path = VALUES(local_path)
`, seed.ModelName, seed.DisplayName, seed.ModelType, seed.ServiceName, seed.Status, seed.Description, seed.DefaultPositivePrompt, seed.DefaultNegativePrompt, seed.LocalPath); r.schemaErr != nil {
				return
			}
		}
	})
	return r.schemaErr
}

// isIgnorableMigrationError 忽略重复列与重复索引带来的幂等迁移错误。
func isIgnorableMigrationError(err error) bool {
	var mysqlErr *mysqlDriver.MySQLError
	if !errors.As(err, &mysqlErr) {
		return false
	}
	return mysqlErr.Number == 1060 || mysqlErr.Number == 1061
}

// ListCatalog 返回模型中心的完整目录列表。
func (r *ModelRepository) ListCatalog(ctx context.Context) ([]model.RegistryModel, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return nil, err
	}

	const query = `
SELECT id, model_name, display_name, model_type, service_name, status, COALESCE(description, ''), COALESCE(default_positive_prompt, ''), COALESCE(default_negative_prompt, ''), COALESCE(local_path, '')
FROM model_registry
ORDER BY id ASC
`

	rows, err := r.db.QueryContext(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	items := make([]model.RegistryModel, 0)
	for rows.Next() {
		var item model.RegistryModel
		if err := rows.Scan(
			&item.ID,
			&item.ModelName,
			&item.DisplayName,
			&item.ModelType,
			&item.ServiceName,
			&item.Status,
			&item.Description,
			&item.DefaultPositivePrompt,
			&item.DefaultNegativePrompt,
			&item.LocalPath,
		); err != nil {
			return nil, err
		}
		items = append(items, item)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	return items, nil
}

// GetByName 根据模型名查询单条注册表记录。
func (r *ModelRepository) GetByName(ctx context.Context, modelName string) (model.RegistryModel, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.RegistryModel{}, err
	}

	const query = `
SELECT id, model_name, display_name, model_type, service_name, status, COALESCE(description, ''), COALESCE(default_positive_prompt, ''), COALESCE(default_negative_prompt, ''), COALESCE(local_path, '')
FROM model_registry
WHERE model_name = ?
`

	var item model.RegistryModel
	if err := r.db.QueryRowContext(ctx, query, modelName).Scan(
		&item.ID,
		&item.ModelName,
		&item.DisplayName,
		&item.ModelType,
		&item.ServiceName,
		&item.Status,
		&item.Description,
		&item.DefaultPositivePrompt,
		&item.DefaultNegativePrompt,
		&item.LocalPath,
	); err != nil {
		return model.RegistryModel{}, err
	}
	return item, nil
}
