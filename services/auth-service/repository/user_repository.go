package repository

import (
	"context"
	"database/sql"

	"electric-ai/services/auth-service/model"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) FindByUsername(ctx context.Context, username string) (*model.User, error) {
	const query = `
SELECT id, username, password_hash, display_name, status
FROM auth_users
WHERE username = ?
LIMIT 1
`

	var user model.User
	if err := r.db.QueryRowContext(ctx, query, username).Scan(
		&user.ID,
		&user.Username,
		&user.PasswordHash,
		&user.DisplayName,
		&user.Status,
	); err != nil {
		return nil, err
	}

	return &user, nil
}
