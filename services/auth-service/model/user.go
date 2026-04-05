package model

type User struct {
	ID           int64
	Username     string
	PasswordHash string
	DisplayName  string
	Status       string
}
