FROM golang:1.27-alpine AS build

WORKDIR /app
COPY . .
RUN go mod init example.com/backend-go-template || true
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o app ./src/main.go

FROM alpine:3.24
RUN apk --no-cache add ca-certificates \
    && addgroup -S app \
    && adduser -S -G app app
WORKDIR /app
COPY --from=build --chown=app:app /app/app .
USER app
EXPOSE 8080
CMD ["./app"]
