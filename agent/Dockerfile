FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod ./
RUN go mod download || true
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o agent ./cmd/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates \
    && addgroup -S appuser && adduser -S appuser -G appuser

WORKDIR /home/appuser
COPY --from=builder /app/agent .
RUN chown appuser:appuser agent

USER appuser

EXPOSE 8080
CMD ["./agent"]