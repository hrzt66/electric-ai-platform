FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/audit-service
RUN go build -o /out/audit-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/audit-service /srv/audit-service
CMD ["/srv/audit-service"]
