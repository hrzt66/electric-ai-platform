FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/gateway-service
RUN go build -o /out/gateway-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/gateway-service /srv/gateway-service
CMD ["/srv/gateway-service"]
