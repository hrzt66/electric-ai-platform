FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/task-service
RUN go build -o /out/task-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/task-service /srv/task-service
CMD ["/srv/task-service"]
