FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/asset-service
RUN go build -o /out/asset-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/asset-service /srv/asset-service
CMD ["/srv/asset-service"]
