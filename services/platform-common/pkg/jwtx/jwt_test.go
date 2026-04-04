package jwtx

import (
	"testing"

	"github.com/golang-jwt/jwt/v5"
)

func TestIssueCreatesSignedTokenParsableWithSameSecret(t *testing.T) {
	secret := "test-secret"

	tokenString, err := Issue(secret, "user-1", "alice", 10)
	if err != nil {
		t.Fatalf("expected token issue success, got %v", err)
	}
	if tokenString == "" {
		t.Fatalf("expected non-empty token string")
	}

	parsed, err := jwt.Parse(tokenString, func(token *jwt.Token) (any, error) {
		return []byte(secret), nil
	})
	if err != nil {
		t.Fatalf("expected token parse success, got %v", err)
	}
	if !parsed.Valid {
		t.Fatalf("expected parsed token to be valid")
	}

	claims, ok := parsed.Claims.(jwt.MapClaims)
	if !ok {
		t.Fatalf("expected map claims")
	}
	if claims["user_id"] != "user-1" {
		t.Fatalf("expected user_id claim user-1, got %v", claims["user_id"])
	}
	if claims["username"] != "alice" {
		t.Fatalf("expected username claim alice, got %v", claims["username"])
	}
}
