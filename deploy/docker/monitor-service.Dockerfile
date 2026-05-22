FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/monitor-service
RUN go build -o /out/monitor-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/monitor-service /srv/monitor-service
CMD ["/srv/monitor-service"]

