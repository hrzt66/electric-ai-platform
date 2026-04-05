FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/auth-service
RUN go build -o /out/auth-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/auth-service /srv/auth-service
CMD ["/srv/auth-service"]
