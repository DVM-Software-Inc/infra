FROM golang:1.22 as build

WORKDIR /app
COPY . .
RUN go mod init example.com/backend-go-template || true
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o app ./src/main.go

FROM alpine:3.20
WORKDIR /app
COPY --from=build /app/app .
EXPOSE 8080
CMD ["./app"]
