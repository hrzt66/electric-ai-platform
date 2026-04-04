package jwtx

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func Issue(secret, userID, username string, expireMinutes int) (string, error) {
	claims := jwt.MapClaims{
		"user_id":  userID,
		"username": username,
		"exp":      time.Now().Add(time.Duration(expireMinutes) * time.Minute).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secret))
}
