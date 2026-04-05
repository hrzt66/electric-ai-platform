FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/model-service
RUN go build -o /out/model-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/model-service /srv/model-service
CMD ["/srv/model-service"]
