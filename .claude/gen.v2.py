#!/usr/bin/env python3
"""
tracepoint-m project skeleton generator
"""

import os
import stat

ROOT = "tracepoint-m"

DIRS = [
    "cmd/server",
    "cmd/cli",
    "internal/api/handler",
    "internal/api/middleware",
    "internal/api/router",
    "internal/auth",
    "internal/storage/s3",
    "internal/storage/fs",
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
    "deploy/docker",
    "deploy/k8s/base",
    "deploy/k8s/overlays/dev",
    "deploy/k8s/overlays/prod",
    "deploy/compose",
    "scripts",
    "docs",
    "test/integration",
    "test/api",
    ".gitlab",
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
\tBackend   string `yaml:"backend"` // s3 | fs
\tS3Bucket  string `yaml:"s3_bucket"`
\tS3Region  string `yaml:"s3_region"`
\tS3Endpoint string `yaml:"s3_endpoint"`
\tFSRoot    string `yaml:"fs_root"`
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
  dsn: "postgres://tracepoint:tracepoint@localhost:5432/tracepoint?sslmode=disable"

storage:
  backend: "s3"
  s3_bucket: "tracepoint-artifacts"
  s3_region: "us-east-1"
  s3_endpoint: "http://localhost:9000"  # minio / ceph / etc
  fs_root: "/var/lib/tracepoint/artifacts"

auth:
  jwt_secret: "changeme"

redis:
  addr: "localhost:6379"
""",

    # -------------------------------------------------------------------------
    # Storage interfaces
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

type S3Backend struct{}

func New() *S3Backend { return &S3Backend{} }

func (s *S3Backend) Put(_ context.Context, _ string, _ io.Reader, _ int64) error { return nil }
func (s *S3Backend) Get(_ context.Context, _ string) (io.ReadCloser, error)      { return nil, nil }
func (s *S3Backend) Delete(_ context.Context, _ string) error                    { return nil }
func (s *S3Backend) Exists(_ context.Context, _ string) (bool, error)            { return false, nil }
""",

    "internal/storage/fs/fs.go": """\
package fs

import (
\t"context"
\t"io"
)

type FSBackend struct {
\tRoot string
}

func New(root string) *FSBackend { return &FSBackend{Root: root} }

func (f *FSBackend) Put(_ context.Context, _ string, _ io.Reader, _ int64) error { return nil }
func (f *FSBackend) Get(_ context.Context, _ string) (io.ReadCloser, error)      { return nil, nil }
func (f *FSBackend) Delete(_ context.Context, _ string) error                    { return nil }
func (f *FSBackend) Exists(_ context.Context, _ string) (bool, error)            { return false, nil }
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
\tUserID string `json:"user_id"`
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
\tEventLogin           EventType = "login"
\tEventTokenIssued     EventType = "token_issued"
\tEventArtifactUpload  EventType = "artifact_upload"
\tEventArtifactDelete  EventType = "artifact_delete"
\tEventPermissionChange EventType = "permission_change"
\tEventAdminAction     EventType = "admin_action"
)

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
\tAfter  string `json:"after,omitempty"`
\tLimit  int    `json:"limit"`
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
    # First migration
    # -------------------------------------------------------------------------
    "db/migrations/00001_init.sql": """\
-- +goose Up

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE service_accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    token_hash  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE repositories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    format      TEXT NOT NULL,  -- maven, pypi, npm, oci, yum, debian, generic
    type        TEXT NOT NULL,  -- hosted, proxy, group
    config      JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
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

CREATE TABLE audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    actor_id   TEXT NOT NULL,
    resource   TEXT,
    meta       JSONB NOT NULL DEFAULT '{}',
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
    # Makefile
    # -------------------------------------------------------------------------
    "Makefile": """\
BINARY_SERVER   := tracepoint-server
BINARY_CLI      := tracepoint-cli
BUILD_DIR       := ./bin
VERSION         ?= dev
COMMIT          ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo none)
BUILD_TIME      ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS         := -X github.com/yourorg/tracepoint-m/pkg/version.Version=$(VERSION) \\
                   -X github.com/yourorg/tracepoint-m/pkg/version.Commit=$(COMMIT) \\
                   -X github.com/yourorg/tracepoint-m/pkg/version.BuildTime=$(BUILD_TIME)

.PHONY: all build build-server build-cli run test lint fmt vet tidy clean \
        migrate-up migrate-down docker-build compose-up compose-down rpm

all: build

build: build-server build-cli

build-server:
\tgo build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER) ./cmd/server

build-cli:
\tgo build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLI) ./cmd/cli

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
\tdocker build -t tracepoint-m:$(VERSION) .

compose-up:
\tdocker compose -f deploy/compose/docker-compose.yml up -d

compose-down:
\tdocker compose -f deploy/compose/docker-compose.yml down

rpm:
\tbash scripts/build-rpm.sh
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
    -o /bin/tracepoint-server ./cmd/server

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=builder /bin/tracepoint-server /usr/local/bin/tracepoint-server
EXPOSE 8080
ENTRYPOINT ["tracepoint-server"]
""",

    ".dockerignore": """\
bin/
*.rpm
*.tar.gz
.git/
web/node_modules/
""",

    # -------------------------------------------------------------------------
    # Docker Compose
    # -------------------------------------------------------------------------
    "deploy/compose/docker-compose.yml": """\
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: tracepoint
      POSTGRES_PASSWORD: tracepoint
      POSTGRES_DB: tracepoint
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: quay.io/minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  server:
    build:
      context: ../../
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      DATABASE_DSN: postgres://tracepoint:tracepoint@postgres:5432/tracepoint?sslmode=disable
    depends_on:
      - postgres
      - redis
      - minio

volumes:
  pg_data:
  minio_data:
""",

    # -------------------------------------------------------------------------
    # Kubernetes base
    # -------------------------------------------------------------------------
    "deploy/k8s/base/deployment.yaml": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tracepoint-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tracepoint-server
  template:
    metadata:
      labels:
        app: tracepoint-server
    spec:
      containers:
        - name: server
          image: tracepoint-m:latest
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: tracepoint-secrets
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
""",

    "deploy/k8s/base/service.yaml": """\
apiVersion: v1
kind: Service
metadata:
  name: tracepoint-server
spec:
  selector:
    app: tracepoint-server
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
""",

    "deploy/k8s/base/kustomization.yaml": """\
resources:
  - deployment.yaml
  - service.yaml
""",

    "deploy/k8s/overlays/dev/kustomization.yaml": """\
bases:
  - ../../base
patches: []
""",

    "deploy/k8s/overlays/prod/kustomization.yaml": """\
bases:
  - ../../base
patches: []
""",

    # -------------------------------------------------------------------------
    # RPM spec
    # -------------------------------------------------------------------------
    "deploy/rpm/tracepoint-m.spec": """\
Name:           tracepoint-m
Version:        %{version}
Release:        1%{?dist}
Summary:        Modern artifact repository and supply-chain platform
License:        Proprietary
URL:            https://github.com/yourorg/tracepoint-m
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  golang >= 1.22
Requires:       systemd

%description
tracepoint-m is a modern artifact repository platform supporting Maven, PyPI,
npm, OCI, yum, Debian, and generic blob formats.

%prep
%setup -q

%build
make build-server VERSION=%{version} COMMIT=%{commit}

%install
install -D -m 0755 bin/tracepoint-server %{buildroot}/usr/local/bin/tracepoint-server
install -D -m 0644 deploy/rpm/tracepoint-m.service %{buildroot}/usr/lib/systemd/system/tracepoint-m.service
install -D -m 0640 config.yaml %{buildroot}/etc/tracepoint-m/config.yaml

%post
%systemd_post tracepoint-m.service

%preun
%systemd_preun tracepoint-m.service

%postun
%systemd_postun_with_restart tracepoint-m.service

%files
/usr/local/bin/tracepoint-server
/usr/lib/systemd/system/tracepoint-m.service
%config(noreplace) /etc/tracepoint-m/config.yaml

%changelog
* $(date '+%a %b %d %Y') CI <ci@yourorg.com> - %{version}-1
- Automated build
""",

    "deploy/rpm/tracepoint-m.service": """\
[Unit]
Description=tracepoint-m artifact repository
After=network.target

[Service]
Type=simple
User=tracepoint
ExecStart=/usr/local/bin/tracepoint-server
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
EnvironmentFile=-/etc/tracepoint-m/env

[Install]
WantedBy=multi-user.target
""",

    # -------------------------------------------------------------------------
    # RPM build script
    # -------------------------------------------------------------------------
    "scripts/build-rpm.sh": """\
#!/usr/bin/env bash
set -euo pipefail

VERSION="${VERSION:-0.1.0}"
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "none")
SPEC="deploy/rpm/tracepoint-m.spec"
TOPDIR="$HOME/rpmbuild"

mkdir -p "$TOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
TARNAME="tracepoint-m-${VERSION}"
git archive --format=tar.gz --prefix="${TARNAME}/" HEAD > "$TOPDIR/SOURCES/${TARNAME}.tar.gz"

cp "$SPEC" "$TOPDIR/SPECS/"

rpmbuild -ba "$TOPDIR/SPECS/tracepoint-m.spec" \\
    --define "version ${VERSION}" \\
    --define "commit ${COMMIT}" \\
    --define "_topdir ${TOPDIR}"

echo "RPM built:"
find "$TOPDIR/RPMS" -name "*.rpm"
""",

    "scripts/install-rpm-tooling.sh": """\
#!/usr/bin/env bash
# Install RPM build tooling on RHEL/Rocky/AlmaLinux/OracleLinux
set -euo pipefail

if ! command -v rpmbuild &>/dev/null; then
    dnf install -y rpm-build rpm-devel rpmdevtools rpmlint
fi

if ! command -v go &>/dev/null; then
    dnf install -y golang
fi

if ! command -v goose &>/dev/null; then
    go install github.com/pressly/goose/v3/cmd/goose@latest
fi

if ! command -v golangci-lint &>/dev/null; then
    curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b "$(go env GOPATH)/bin"
fi

rpmdev-setuptree
echo "RPM tooling ready."
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

stages:
  - lint
  - test
  - build
  - package
  - publish

cache:
  paths:
    - .cache/go/pkg/mod/

before_script:
  - export GOPATH="$CI_PROJECT_DIR/.cache/go"
  - export PATH="$GOPATH/bin:$PATH"

# ---------------------------------------------------------------------------
lint:
  stage: lint
  script:
    - go vet ./...
    - |
      if ! command -v golangci-lint &>/dev/null; then
        curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b "$GOPATH/bin"
      fi
    - golangci-lint run ./...

# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
build:
  stage: build
  script:
    - make build VERSION="$CI_COMMIT_TAG" COMMIT="$CI_COMMIT_SHORT_SHA"
  artifacts:
    paths:
      - bin/
    expire_in: 1 day

# ---------------------------------------------------------------------------
package:rpm:
  stage: package
  image: rockylinux:9
  rules:
    - if: '$CI_COMMIT_TAG'
  before_script:
    - dnf install -y rpm-build rpm-devel rpmdevtools golang git
    - rpmdev-setuptree
  script:
    - VERSION="$CI_COMMIT_TAG" bash scripts/build-rpm.sh
  artifacts:
    paths:
      - "*.rpm"
    expire_in: 30 days

# ---------------------------------------------------------------------------
publish:rpm:
  stage: publish
  image: rockylinux:9
  rules:
    - if: '$CI_COMMIT_TAG'
  needs:
    - package:rpm
  script:
    - |
      # Upload to GitLab Generic Package Registry
      for rpm in $(find $HOME/rpmbuild/RPMS -name "*.rpm"); do
        fname=$(basename "$rpm")
        curl --header "JOB-TOKEN: $CI_JOB_TOKEN" \\
             --upload-file "$rpm" \\
             "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/generic/tracepoint-m/${CI_COMMIT_TAG}/${fname}"
      done
""",

    # -------------------------------------------------------------------------
    # .gitignore
    # -------------------------------------------------------------------------
    ".gitignore": """\
bin/
*.rpm
*.tar.gz
*.out
.cache/
vendor/
web/node_modules/
web/dist/
.env
""",

    # -------------------------------------------------------------------------
    # golangci-lint config
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # go.sum placeholder
    # -------------------------------------------------------------------------
    "go.sum": "",
}

EXECUTABLES = {
    "scripts/build-rpm.sh",
    "scripts/install-rpm-tooling.sh",
}


def create_skeleton():
    os.makedirs(ROOT, exist_ok=True)

    for d in DIRS:
        path = os.path.join(ROOT, d)
        os.makedirs(path, exist_ok=True)
        gitkeep = os.path.join(path, ".gitkeep")
        if not os.listdir(path):
            open(gitkeep, "w").close()

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