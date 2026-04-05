package service

import (
	"context"
	"testing"
)

type stubUserRepo struct {
	user *LoginUser
}

func (s *stubUserRepo) FindByUsername(_ context.Context, username string) (*LoginUser, error) {
	if s.user != nil && s.user.Username == username {
		return s.user, nil
	}
	return nil, ErrInvalidCredentials
}

func TestLoginReturnsTokenForValidUser(t *testing.T) {
	repo := &stubUserRepo{
		user: &LoginUser{
			ID:           1,
			Username:     "admin",
			DisplayName:  "System Admin",
			PasswordHash: "$2b$10$ydMkvQ83zoqHxjJmCcviaupmIqse4rfj3k2eujOWeQgitZoSil05a",
			Status:       "active",
		},
	}

	svc := NewAuthService(repo, "electric-ai-secret")
	result, err := svc.Login(context.Background(), LoginRequest{
		Username: "admin",
		Password: "admin123456",
	})
	if err != nil {
		t.Fatalf("expected login success, got %v", err)
	}
	if result.AccessToken == "" {
		t.Fatal("expected non-empty access token")
	}
}
