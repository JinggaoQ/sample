FROM golang:1.18-alpine

ARG VERSION=1.7.4.3-r0
RUN apk --no-cache add socat=${VERSION}

WORKDIR /app

COPY run.sh ./
COPY go.mod ./
COPY go.sum ./
RUN go mod download
COPY *.go ./

RUN go build -o /httptest

EXPOSE 8888

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
