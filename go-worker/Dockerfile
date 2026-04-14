FROM golang:1.23-alpine AS builder

WORKDIR /src
COPY go-worker/go.mod ./go.mod
COPY go-worker/main.go ./main.go
RUN go build -o /out/tsp-go-worker ./main.go

FROM alpine:3.20
WORKDIR /app
COPY --from=builder /out/tsp-go-worker /usr/local/bin/tsp-go-worker
EXPOSE 8080
CMD ["tsp-go-worker"]
