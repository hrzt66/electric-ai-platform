package service

import (
	"context"
	"errors"
	"strconv"
	"strings"

	"golang.org/x/crypto/bcrypt"

	"electric-ai/services/auth-service/model"
	"electric-ai/services/platform-common/pkg/jwtx"
)

var ErrInvalidCredentials = errors.New("invalid credentials")

type LoginUser = model.User
type LoginRequest = model.LoginRequest
type LoginResponse = model.LoginResponse

type UserRepository interface {
	FindByUsername(ctx context.Context, username string) (*LoginUser, error)
}

type AuthService struct {
	repo      UserRepository
	jwtSecret string
}

func NewAuthService(repo UserRepository, jwtSecret string) *AuthService {
	return &AuthService{
		repo:      repo,
		jwtSecret: jwtSecret,
	}
}

func (s *AuthService) Login(ctx context.Context, req LoginRequest) (LoginResponse, error) {
	username := strings.TrimSpace(req.Username)
	password := strings.TrimSpace(req.Password)
	if username == "" || password == "" {
		return LoginResponse{}, ErrInvalidCredentials
	}

	user, err := s.repo.FindByUsername(ctx, username)
	if err != nil || user == nil {
		return LoginResponse{}, ErrInvalidCredentials
	}
	if user.Status != "active" {
		return LoginResponse{}, ErrInvalidCredentials
	}
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)); err != nil {
		return LoginResponse{}, ErrInvalidCredentials
	}

	token, err := jwtx.Issue(s.jwtSecret, strconv.FormatInt(user.ID, 10), user.Username, 120)
	if err != nil {
		return LoginResponse{}, err
	}

	return LoginResponse{
		AccessToken: token,
		UserName:    user.Username,
		DisplayName: user.DisplayName,
	}, nil
}
