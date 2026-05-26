#!/usr/bin/env python3
"""
tracepoint-m project skeleton generator
Deployment model: single-node Docker Compose + NGINX
"""

import os
import stat

ROOT = "tracepoint-m"

DIRS = [
    "cmd/server",
    "cmd/worker",
    "cmd/cli",
    "internal/api/handler",
    "internal/api/middleware",
    "internal/api/router",
    "internal/auth",
    "internal/storage/s3",
    "internal/repo/maven",
    "internal/repo/pypi",
    "internal/repo/npm",
    "internal/repo/oci",
    "internal/repo/yum",
    "internal/repo/debian",
    "internal/repo/generic",
    "internal/search",
    "internal/workers",
    "internal/events",
    "internal/audit",
    "internal/rbac",
    "internal/config",
    "internal/errors",
    "pkg/logger",
    "pkg/pagination",
    "pkg/validator",
    "pkg/version",
    "web/src",
    "web/public",
    "db/migrations",
    "db/queries",
    "deploy/nginx/conf.d",
    "deploy/compose",
    "scripts",
    "docs",
    "test/integration",
    "test/api",
]

FILES = {

    # -------------------------------------------------------------------------
    # Go module
    # -------------------------------------------------------------------------
    "go.mod": """\
module github.com/yourorg/tracepoint-m

go 1.22
""",

    # -------------------------------------------------------------------------
    # Entry points
    # -------------------------------------------------------------------------
    "cmd/server/main.go": """\
package main

import "fmt"

func main() {
\tfmt.Println("tracepoint-m server")
}
""",

    "cmd/worker/main.go": """\
package main

import "fmt"

func main() {
\tfmt.Println("tracepoint-m worker")
}
""",

    "cmd/cli/main.go": """\
package main

import "fmt"

func main() {
\tfmt.Println("tracepoint-m cli")
}
""",

    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------
    "internal/config/config.go": """\
package config

import (
\t"os"

\t"gopkg.in/yaml.v3"
)

type Config struct {
\tServer   ServerConfig   `yaml:"server"`
\tDatabase DatabaseConfig `yaml:"database"`
\tStorage  StorageConfig  `yaml:"storage"`
\tAuth     AuthConfig     `yaml:"auth"`
\tRedis    RedisConfig    `yaml:"redis"`
}

type ServerConfig struct {
\tHost string `yaml:"host"`
\tPort int    `yaml:"port"`
}

type DatabaseConfig struct {
\tDSN string `yaml:"dsn"`
}

type StorageConfig struct {
\tS3Endpoint string `yaml:"s3_endpoint"`
\tS3Bucket   string `yaml:"s3_bucket"`
\tS3Region   string `yaml:"s3_region"`
}

type AuthConfig struct {
\tJWTSecret string `yaml:"jwt_secret"`
}

type RedisConfig struct {
\tAddr string `yaml:"addr"`
}

func Load(path string) (*Config, error) {
\tf, err := os.Open(path)
\tif err != nil {
\t\treturn nil, err
\t}
\tdefer f.Close()
\tvar cfg Config
\treturn &cfg, yaml.NewDecoder(f).Decode(&cfg)
}
""",

    "config.yaml": """\
server:
  host: "0.0.0.0"
  port: 8080

database:
  dsn: "postgres://tracepoint:tracepoint@postgres:5432/tracepoint?sslmode=disable"

storage:
  s3_endpoint: ""         # set via env S3_ENDPOINT
  s3_bucket: ""           # set via env S3_BUCKET
  s3_region: "us-east-1"  # set via env S3_REGION

auth:
  jwt_secret: ""          # MUST be set via env AUTH_JWT_SECRET — never commit a value here

redis:
  addr: "redis:6379"
""",

    # -------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------
    "internal/storage/storage.go": """\
package storage

import (
\t"context"
\t"io"
)

type Backend interface {
\tPut(ctx context.Context, key string, r io.Reader, size int64) error
\tGet(ctx context.Context, key string) (io.ReadCloser, error)
\tDelete(ctx context.Context, key string) error
\tExists(ctx context.Context, key string) (bool, error)
}
""",

    "internal/storage/s3/s3.go": """\
package s3

import (
\t"context"
\t"io"
)

// S3Backend implements storage.Backend against any S3-compatible endpoint.
// Credentials loaded from environment by the AWS SDK:
//   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
type S3Backend struct {
\tEndpoint string
\tBucket   string
\tRegion   string
}

func New(endpoint, bucket, region string) *S3Backend {
\treturn &S3Backend{Endpoint: endpoint, Bucket: bucket, Region: region}
}

func (s *S3Backend) Put(_ context.Context, _ string, _ io.Reader, _ int64) error { return nil }
func (s *S3Backend) Get(_ context.Context, _ string) (io.ReadCloser, error)      { return nil, nil }
func (s *S3Backend) Delete(_ context.Context, _ string) error                    { return nil }
func (s *S3Backend) Exists(_ context.Context, _ string) (bool, error)            { return false, nil }
""",

    # -------------------------------------------------------------------------
    # Repo engine interface
    # -------------------------------------------------------------------------
    "internal/repo/engine.go": """\
package repo

import (
\t"context"
\t"io"
)

type Engine interface {
\tUpload(ctx context.Context, path string, r io.Reader) error
\tDownload(ctx context.Context, path string) (io.ReadCloser, error)
\tValidate(ctx context.Context, path string, r io.Reader) error
\tExtractMetadata(ctx context.Context, path string) (map[string]string, error)
}
""",

    # -------------------------------------------------------------------------
    # Auth
    # -------------------------------------------------------------------------
    "internal/auth/auth.go": """\
package auth

import (
\t"errors"
\t"time"

\t"github.com/golang-jwt/jwt/v5"
)

var ErrInvalidToken = errors.New("invalid token")

type Claims struct {
\tUserID string   `json:"user_id"`
\tRoles  []string `json:"roles"`
\tjwt.RegisteredClaims
}

func IssueToken(secret, userID string, roles []string, ttl time.Duration) (string, error) {
\tclaims := Claims{
\t\tUserID: userID,
\t\tRoles:  roles,
\t\tRegisteredClaims: jwt.RegisteredClaims{
\t\t\tExpiresAt: jwt.NewNumericDate(time.Now().Add(ttl)),
\t\t},
\t}
\treturn jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString([]byte(secret))
}

func ValidateToken(secret, tokenStr string) (*Claims, error) {
\ttoken, err := jwt.ParseWithClaims(tokenStr, &Claims{}, func(t *jwt.Token) (interface{}, error) {
\t\tif _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
\t\t\treturn nil, ErrInvalidToken
\t\t}
\t\treturn []byte(secret), nil
\t})
\tif err != nil || !token.Valid {
\t\treturn nil, ErrInvalidToken
\t}
\treturn token.Claims.(*Claims), nil
}
""",

    # -------------------------------------------------------------------------
    # RBAC
    # -------------------------------------------------------------------------
    "internal/rbac/rbac.go": """\
package rbac

type Action string
type Resource string

const (
\tActionRead   Action = "read"
\tActionWrite  Action = "write"
\tActionDelete Action = "delete"
\tActionAdmin  Action = "admin"
)

type Policy struct {
\tRole     string
\tResource Resource
\tAction   Action
}

type Enforcer interface {
\tAllow(role string, resource Resource, action Action) bool
}
""",

    # -------------------------------------------------------------------------
    # Errors
    # -------------------------------------------------------------------------
    "internal/errors/errors.go": """\
package errors

import "fmt"

type APIError struct {
\tCode    string `json:"code"`
\tMessage string `json:"message"`
}

func (e *APIError) Error() string {
\treturn fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func NotFound(resource string) *APIError {
\treturn &APIError{Code: resource + "_not_found", Message: resource + " does not exist"}
}

func Unauthorized() *APIError {
\treturn &APIError{Code: "unauthorized", Message: "unauthorized"}
}

func BadRequest(msg string) *APIError {
\treturn &APIError{Code: "bad_request", Message: msg}
}
""",

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------
    "internal/audit/audit.go": """\
package audit

import (
\t"context"
\t"time"
)

type EventType string

const (
\tEventLogin            EventType = "login"
\tEventTokenIssued      EventType = "token_issued"
\tEventArtifactUpload   EventType = "artifact_upload"
\tEventArtifactDelete   EventType = "artifact_delete"
\tEventPermissionChange EventType = "permission_change"
\tEventAdminAction      EventType = "admin_action"
)

// Event is written synchronously to PostgreSQL.
// Never routed through the event bus.
type Event struct {
\tID        string
\tType      EventType
\tActorID   string
\tResource  string
\tMeta      map[string]string
\tTimestamp time.Time
}

type Logger interface {
\tLog(ctx context.Context, e Event) error
}
""",

    # -------------------------------------------------------------------------
    # Logger
    # -------------------------------------------------------------------------
    "pkg/logger/logger.go": """\
package logger

import (
\t"log/slog"
\t"os"
)

func New(level slog.Level) *slog.Logger {
\treturn slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: level}))
}
""",

    # -------------------------------------------------------------------------
    # Pagination
    # -------------------------------------------------------------------------
    "pkg/pagination/pagination.go": """\
package pagination

type Cursor struct {
\tAfter string `json:"after,omitempty"`
\tLimit int    `json:"limit"`
}

type Page[T any] struct {
\tItems      []T    `json:"items"`
\tNextCursor string `json:"next_cursor,omitempty"`
\tHasMore    bool   `json:"has_more"`
}
""",

    # -------------------------------------------------------------------------
    # Version
    # -------------------------------------------------------------------------
    "pkg/version/version.go": """\
package version

var (
\tVersion   = "dev"
\tCommit    = "none"
\tBuildTime = "unknown"
)
""",

    # -------------------------------------------------------------------------
    # Migration
    # -------------------------------------------------------------------------
    "db/migrations/00001_init.sql": """\
-- +goose Up

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE service_accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    token_hash  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE repositories (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL UNIQUE,
    format     TEXT NOT NULL,  -- maven | pypi | npm | oci | yum | debian | generic
    type       TEXT NOT NULL,  -- hosted | proxy
    config     JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE artifacts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id      UUID NOT NULL REFERENCES repositories(id),
    path         TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    size         BIGINT NOT NULL,
    content_type TEXT NOT NULL,
    metadata     JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repo_id, path)
);

CREATE TABLE roles (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

-- append-only; no updates or deletes ever on this table
CREATE TABLE audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT        NOT NULL,
    actor_id   TEXT        NOT NULL,
    resource   TEXT,
    meta       JSONB       NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- +goose Down

DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS artifacts;
DROP TABLE IF EXISTS repositories;
DROP TABLE IF EXISTS service_accounts;
DROP TABLE IF EXISTS users;
""",

    # -------------------------------------------------------------------------
    # NGINX
    # -------------------------------------------------------------------------
    "deploy/nginx/nginx.conf": """\
user  nginx;
worker_processes  auto;
error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;

events {
    worker_connections 4096;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile       on;
    keepalive_timeout 65;

    client_max_body_size 0;

    include /etc/nginx/conf.d/*.conf;
}
""",

    "deploy/nginx/conf.d/tracepoint.conf": """\
upstream tracepoint_api {
    server server:8080;
}

upstream tracepoint_web {
    server web:3000;
}

server {
    listen 80;
    server_name _;

    # OCI / Docker registry protocol
    location /v2/ {
        proxy_pass                http://tracepoint_api;
        proxy_set_header          Host              $host;
        proxy_set_header          X-Real-IP         $remote_addr;
        proxy_set_header          X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header          X-Forwarded-Proto $scheme;
        proxy_request_buffering   off;
        proxy_buffering           off;
        client_max_body_size      0;
    }

    # REST API
    location /api/ {
        proxy_pass                http://tracepoint_api;
        proxy_set_header          Host              $host;
        proxy_set_header          X-Real-IP         $remote_addr;
        proxy_set_header          X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header          X-Forwarded-Proto $scheme;
        proxy_request_buffering   off;
        proxy_buffering           off;
        client_max_body_size      0;
    }

    location /healthz {
        proxy_pass http://tracepoint_api;
    }

    # Web UI
    location / {
        proxy_pass       http://tracepoint_web;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
""",

    # -------------------------------------------------------------------------
    # Docker Compose
    # -------------------------------------------------------------------------
    "deploy/compose/docker-compose.yml": """\
# tracepoint-m — single-node Docker Compose
# S3-compatible storage is EXTERNAL — configure via .env
#
# Required environment variables:
#   AUTH_JWT_SECRET
#   S3_ENDPOINT
#   S3_BUCKET
#   S3_REGION
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY

services:

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ../nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ../nginx/conf.d:/etc/nginx/conf.d:ro
      - nginx_logs:/var/log/nginx
      # - /etc/ssl/tracepoint:/etc/ssl/tracepoint:ro
    depends_on:
      - server
      - web
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: tracepoint
      POSTGRES_PASSWORD: tracepoint
      POSTGRES_DB: tracepoint
    volumes:
      - pg_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tracepoint"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --save "" --appendonly no
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  migrate:
    image: ghcr.io/yourorg/tracepoint-m:${IMAGE_TAG:-latest}
    command: ["migrate"]
    environment:
      DATABASE_DSN: postgres://tracepoint:tracepoint@postgres:5432/tracepoint?sslmode=disable
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"

  server:
    image: ghcr.io/yourorg/tracepoint-m:${IMAGE_TAG:-latest}
    command: ["server"]
    environment:
      DATABASE_DSN: postgres://tracepoint:tracepoint@postgres:5432/tracepoint?sslmode=disable
      REDIS_ADDR: redis:6379
      S3_ENDPOINT: ${S3_ENDPOINT}
      S3_BUCKET: ${S3_BUCKET}
      S3_REGION: ${S3_REGION:-us-east-1}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AUTH_JWT_SECRET: ${AUTH_JWT_SECRET}
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/healthz"]
      interval: 15s
      timeout: 5s
      retries: 5

  worker:
    image: ghcr.io/yourorg/tracepoint-m:${IMAGE_TAG:-latest}
    command: ["worker"]
    environment:
      DATABASE_DSN: postgres://tracepoint:tracepoint@postgres:5432/tracepoint?sslmode=disable
      REDIS_ADDR: redis:6379
      S3_ENDPOINT: ${S3_ENDPOINT}
      S3_BUCKET: ${S3_BUCKET}
      S3_REGION: ${S3_REGION:-us-east-1}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AUTH_JWT_SECRET: ${AUTH_JWT_SECRET}
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    restart: unless-stopped

  web:
    image: ghcr.io/yourorg/tracepoint-m-web:${IMAGE_TAG:-latest}
    environment:
      API_BASE_URL: http://server:8080
    restart: unless-stopped

volumes:
  pg_data:
  redis_data:
  nginx_logs:
""",

    "deploy/compose/.env.example": """\
# Copy to .env and fill in. Never commit .env.

IMAGE_TAG=latest

S3_ENDPOINT=https://your-s3-compatible-endpoint
S3_BUCKET=tracepoint-artifacts
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Generate with: openssl rand -hex 32
AUTH_JWT_SECRET=
""",

    # -------------------------------------------------------------------------
    # Dockerfile
    # -------------------------------------------------------------------------
    "Dockerfile": """\
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .

ARG VERSION=dev
ARG COMMIT=none
ARG BUILD_TIME=unknown

RUN go build \\
    -ldflags "-X github.com/yourorg/tracepoint-m/pkg/version.Version=${VERSION} \\
              -X github.com/yourorg/tracepoint-m/pkg/version.Commit=${COMMIT} \\
              -X github.com/yourorg/tracepoint-m/pkg/version.BuildTime=${BUILD_TIME}" \\
    -o /bin/tracepoint ./cmd/server && \\
    go build \\
    -ldflags "-X github.com/yourorg/tracepoint-m/pkg/version.Version=${VERSION} \\
              -X github.com/yourorg/tracepoint-m/pkg/version.Commit=${COMMIT} \\
              -X github.com/yourorg/tracepoint-m/pkg/version.BuildTime=${BUILD_TIME}" \\
    -o /bin/tracepoint-worker ./cmd/worker

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata wget goose
COPY --from=builder /bin/tracepoint        /usr/local/bin/tracepoint
COPY --from=builder /bin/tracepoint-worker /usr/local/bin/tracepoint-worker
COPY db/migrations /migrations

EXPOSE 8080

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["server"]
""",

    ".dockerignore": """\
bin/
*.tar.gz
.git/
web/node_modules/
web/dist/
.env
""",

    # -------------------------------------------------------------------------
    # Entrypoint
    # -------------------------------------------------------------------------
    "scripts/docker-entrypoint.sh": """\
#!/bin/sh
set -e

case "$1" in
  server)
    exec tracepoint
    ;;
  worker)
    exec tracepoint-worker
    ;;
  migrate)
    exec goose -dir /migrations postgres "$DATABASE_DSN" up
    ;;
  *)
    exec "$@"
    ;;
esac
""",

    # -------------------------------------------------------------------------
    # Makefile
    # -------------------------------------------------------------------------
    "Makefile": """\
BINARY        := tracepoint
WORKER_BINARY := tracepoint-worker
CLI_BINARY    := tracepoint-cli
BUILD_DIR     := ./bin
VERSION       ?= dev
COMMIT        ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo none)
BUILD_TIME    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
IMAGE         ?= ghcr.io/yourorg/tracepoint-m
IMAGE_TAG     ?= $(VERSION)

LDFLAGS := -X github.com/yourorg/tracepoint-m/pkg/version.Version=$(VERSION) \\
           -X github.com/yourorg/tracepoint-m/pkg/version.Commit=$(COMMIT) \\
           -X github.com/yourorg/tracepoint-m/pkg/version.BuildTime=$(BUILD_TIME)

.PHONY: all build build-server build-worker build-cli run test lint fmt vet tidy clean \\
        migrate-up migrate-down docker-build compose-up compose-down compose-logs

all: build

build: build-server build-worker build-cli

build-server:
\tgo build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY) ./cmd/server

build-worker:
\tgo build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(WORKER_BINARY) ./cmd/worker

build-cli:
\tgo build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(CLI_BINARY) ./cmd/cli

run:
\tgo run ./cmd/server

test:
\tgo test ./... -race -cover

lint:
\tgolangci-lint run ./...

fmt:
\tgofmt -w .

vet:
\tgo vet ./...

tidy:
\tgo mod tidy

clean:
\trm -rf $(BUILD_DIR)

migrate-up:
\tgoose -dir db/migrations postgres "$(DATABASE_DSN)" up

migrate-down:
\tgoose -dir db/migrations postgres "$(DATABASE_DSN)" down

docker-build:
\tdocker build \\
\t\t--build-arg VERSION=$(VERSION) \\
\t\t--build-arg COMMIT=$(COMMIT) \\
\t\t--build-arg BUILD_TIME=$(BUILD_TIME) \\
\t\t-t $(IMAGE):$(IMAGE_TAG) .

compose-up:
\tdocker compose -f deploy/compose/docker-compose.yml up -d

compose-down:
\tdocker compose -f deploy/compose/docker-compose.yml down

compose-logs:
\tdocker compose -f deploy/compose/docker-compose.yml logs -f
""",

    # -------------------------------------------------------------------------
    # GitLab CI
    # -------------------------------------------------------------------------
    ".gitlab-ci.yml": """\
default:
  image: golang:1.22

variables:
  CGO_ENABLED: "0"
  GOFLAGS: "-mod=readonly"
  DATABASE_DSN: "postgres://tracepoint:tracepoint@postgres:5432/tracepoint?sslmode=disable"
  IMAGE: "ghcr.io/yourorg/tracepoint-m"

stages:
  - lint
  - test
  - build

cache:
  paths:
    - .cache/go/pkg/mod/

before_script:
  - export GOPATH="$CI_PROJECT_DIR/.cache/go"
  - export PATH="$GOPATH/bin:$PATH"

lint:
  stage: lint
  script:
    - go vet ./...
    - |
      curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh \\
        | sh -s -- -b "$GOPATH/bin"
    - golangci-lint run ./...

test:
  stage: test
  services:
    - name: postgres:16-alpine
      alias: postgres
      variables:
        POSTGRES_USER: tracepoint
        POSTGRES_PASSWORD: tracepoint
        POSTGRES_DB: tracepoint
    - name: redis:7-alpine
      alias: redis
  script:
    - go test ./... -race -coverprofile=coverage.out
    - go tool cover -func=coverage.out
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - coverage.out
    expire_in: 7 days
  coverage: '/total:\\s+\\(statements\\)\\s+(\\d+\\.\\d+)%/'

docker:build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - |
      docker build \\
        --build-arg VERSION="${CI_COMMIT_TAG:-$CI_COMMIT_SHORT_SHA}" \\
        --build-arg COMMIT="$CI_COMMIT_SHORT_SHA" \\
        --build-arg BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \\
        -t "$IMAGE:$CI_COMMIT_SHORT_SHA" \\
        -t "$IMAGE:${CI_COMMIT_TAG:-latest}" \\
        .
    - echo "$CI_REGISTRY_PASSWORD" | docker login ghcr.io -u "$CI_REGISTRY_USER" --password-stdin
    - docker push "$IMAGE:$CI_COMMIT_SHORT_SHA"
    - docker push "$IMAGE:${CI_COMMIT_TAG:-latest}"
""",

    # -------------------------------------------------------------------------
    # Misc
    # -------------------------------------------------------------------------
    ".gitignore": """\
bin/
*.tar.gz
*.out
.cache/
vendor/
web/node_modules/
web/dist/
.env
""",

    ".golangci.yml": """\
linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused
    - gofmt
    - goimports
    - misspell

linters-settings:
  gofmt:
    simplify: true

run:
  timeout: 5m
""",

    "go.sum": "",
}

EXECUTABLES = {
    "scripts/docker-entrypoint.sh",
}


def create_skeleton():
    os.makedirs(ROOT, exist_ok=True)

    for d in DIRS:
        path = os.path.join(ROOT, d)
        os.makedirs(path, exist_ok=True)
        if not os.listdir(path):
            open(os.path.join(path, ".gitkeep"), "w").close()

    for rel_path, content in FILES.items():
        abs_path = os.path.join(ROOT, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as f:
            f.write(content)
        if rel_path in EXECUTABLES:
            st = os.stat(abs_path)
            os.chmod(abs_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Skeleton generated at ./{ROOT}/")


if __name__ == "__main__":
    create_skeleton()