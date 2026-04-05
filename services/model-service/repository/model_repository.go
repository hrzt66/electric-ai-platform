package repository

import (
	"context"
	"database/sql"

	"electric-ai/services/model-service/model"
)

type ModelRepository struct {
	db *sql.DB
}

func NewModelRepository(db *sql.DB) *ModelRepository {
	return &ModelRepository{db: db}
}

func (r *ModelRepository) ListActive(ctx context.Context) ([]model.RegistryModel, error) {
	const query = `
SELECT id, model_name, model_type, service_name, status
FROM model_registry
WHERE status = 'active'
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
			&item.ModelType,
			&item.ServiceName,
			&item.Status,
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
