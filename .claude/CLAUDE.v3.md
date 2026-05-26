just clobber v3 and generate.py1:48 PMClaude responded: CLAUDE.CLAUDE.md:
markdown# CLAUDE.md

## Project Overview

Project codename: `tracepoint-m`

A modern artifact repository and software supply-chain platform inspired by Sonatype Nexus, written in Go.

Primary goals:
- Scalability is the #1 priority
- High performance
- Operational simplicity
- Strong API-first design
- Modern RBAC/authentication
- Native OCI/container ecosystem support
- Extensible plugin system
- Strong metadata/indexing/search capabilities

This project is NOT intended to be a Nexus clone. It should modernize the architecture and UX while
supporting common enterprise artifact workflows.

---

# Core Design Principles

## 1. API-first
All functionality must be accessible via:
- REST API
- CLI compatibility layer
- Web UI consuming public APIs only

The UI must never rely on hidden/private backend endpoints.

---

## 2. Stateless application layer
Application nodes should remain as stateless as possible.

Persistent state belongs in:
- PostgreSQL
- External S3-compatible object storage
- Redis (metadata caching only — not a message bus)
- Search/index backend

---

## 3. Storage backend
S3-compatible API is the only supported backend. The specific implementation
(Ceph RadosGW, MinIO, AWS S3, etc.) is external to the platform and configured
via environment variables. The platform does not bundle or manage storage.

Filesystem backend is explicitly out of scope.

---

## 4. Immutable-by-default artifacts
Published artifacts should generally be immutable.

Configurable policies per repository:
- immutable
- overwrite
- append-only
- retention-based

Configurable audit on mutation events.

---

## 5. Global scope to simplify operations
All nodes share the same config source. Config loaded from environment + a single
YAML file, with env taking precedence.

---

## 6. Security is an architectural concern

Required (MVP):
- RBAC
- Token management
- Audit logging (synchronous writes to PostgreSQL, append-only)

Future:
- OIDC/SAML support
- Signed artifacts
- Provenance metadata
- SBOM support

---

## 7. Modular repository engines
Repository formats implemented as isolated modules, behind a common interface.
No global repository-type conditionals. No giant switch statements.

Priorities:
- Maven → 0
- PyPI → 0
- Generic blob → 0
- npm → 1
- OCI/Docker → 1
- yum → 1
- Debian → 1
- Go → 2
- Rust → 2
- NuGet → 3
- Helm → 3
- Others → 4

Metadata sync implemented where feasible (e.g. yum repodata, apt Packages index).

---

# High-Level Architecture

## Deployment Model

Single-node Docker Compose. All services run as containers on one host.
NGINX sits at the front, terminating HTTP and routing to the server container.
                    ┌─────────────────────────────────────┐
                    │            Docker Host               │
                    │                                      │
Client ──────────────▶│  NGINX (80/443)                      │
│     │                                │
│     ├──▶ /api/*         → server:8080│
│     ├──▶ /v2/*  (OCI)   → server:8080│
│     └──▶ /*             → web:3000  │
│                                      │
│  PostgreSQL (5432)                   │
│  Redis      (6379)                   │
│                                      │
│  server ──▶ External S3              │
└─────────────────────────────────────┘

NGINX handles:
- TLS termination (certs mounted as volumes)
- Reverse proxy to API server and web UI
- Streaming passthrough for large uploads (client_max_body_size 0)

The server container is stateless. All persistent state is in PostgreSQL,
Redis (cache only), and the external S3 backend.

Deployment is: `docker compose up -d`. Upgrades are: pull new image, `docker compose up -d`.

---

## Components

### NGINX
- Front router
- TLS termination
- Proxies `/api/*` and `/v2/*` to server
- Proxies `/*` to web UI

---

### API Server
- Authentication
- Authorization
- Routing
- Request validation

---

### Repository Service
- Artifact upload/download
- Metadata
- Repository rules
- Retention policies
- Storage abstraction (S3 only)

---

### Index/Search Service
- Metadata indexing
- Full-text search (PostgreSQL FTS at MVP)
- Tag/version lookup

Post-MVP: OpenSearch or Bleve.

---

### Auth Service
- Local users
- Token issuance
- Service accounts
- JWT validation (centralized)

Future: OIDC, LDAP, SAML — designed for via interfaces, not implemented at MVP.
No external auth platform dependencies.

---

### Background Workers
- Garbage collection
- Retention enforcement
- Indexing
- Scheduled metadata syncs (yum/apt)

Runs as a separate container in compose using the same image, different command.

---

### Event Bus
Redis Streams only. Already a compose dependency for cache.

Scope at MVP: internal indexing triggers only.
Audit writes are NOT routed through the event bus. Audit is synchronous PostgreSQL.

---

# Storage Model

## Metadata
PostgreSQL. Append-only audit table. No blob storage in PG.

Tables:
- users
- service_accounts
- repositories
- artifacts
- roles / user_roles
- audit_log (append-only)

## Blob Storage
External S3-compatible endpoint. Artifacts keyed by content hash:
sha256/ab/cd/<full-digest>

Deduplication is not a platform concern.
Integrity verification is configurable (can be disabled).
GC: platform tracks references, removes unreferenced blobs.

---

# Tech Stack

## Language
Go 1.22+

## HTTP
TBD — chi or echo. No magic.

## Database
PostgreSQL 16. Driver: pgx. Query layer: sqlc. Migrations: goose.

## Object Storage
aws-sdk-go-v2 against any S3-compatible endpoint. All config via environment.

## Cache / Event Bus
Redis 7. Cache only at MVP. Redis Streams for internal async if needed.

## Auth
Internal JWT (HS256). No external auth platform at MVP.

## Observability
Not an MVP priority. slog for structured logging throughout.

## Frontend
TBD — SvelteKit or React. API-driven only, RBAC-aware.

---

# Repository Engine Interface

Each engine exposes:
- Upload handler
- Download handler
- Metadata extraction
- Validation logic
- Retention hooks
- Index hooks

Engines isolated behind interfaces. No global conditionals.

---

# Performance

- Streaming uploads/downloads — no full blob loads into memory
- No temp disk copies where avoidable
- Cursor-based pagination throughout
- No N+1 queries

---

# API Design

## Versioning
/api/v1/

## Pagination
Cursor-based only.

## Errors
```json
{
  "error": {
    "code": "artifact_not_found",
    "message": "artifact does not exist"
  }
}
```

---

# Operational Requirements

## Deployment
Single-node Docker Compose.

## Upgrades
docker compose pull
docker compose up -d

Migrations run as a dedicated compose service that completes before the server starts.

## Backup
- PostgreSQL: pg_dump on a schedule
- S3: handled by the storage backend operator
- Secrets: never in the repo

---

# Security

## Secrets
Passed via environment variables or Docker secrets. Never in config files committed to the repo.

## Input Validation
All uploads validate: size, checksum, content type, path normalization.

## Supply Chain (post-MVP)
Cosign, Sigstore, in-toto attestations, SBOM ingestion.

---

# Code Layout
/cmd
/server
/worker
/cli
/internal
/api
/handler
/middleware
/router
/auth
/storage
/repo
/maven
/pypi
/npm
/oci
/yum
/debian
/generic
/search
/workers
/events
/audit
/rbac
/config
/errors
/pkg
/logger
/pagination
/validator
/version
/web
/db
/migrations
/queries
/deploy
/nginx
/compose
/scripts
/docs
/test
/integration
/api

---

# Non-Goals (MVP)

- Kubernetes / Swarm
- Filesystem storage backend
- External auth platforms
- Replication
- Vulnerability scanning
- Advanced search (beyond PG FTS)
- Group repositories
- Observability stack
- Multi-region / multi-node HA
- RPM packaging

---

# MVP Scope

- Hosted repositories: Maven, PyPI, Generic blob
- OCI registry support
- RBAC + local users + service accounts
- S3 backend (external, configurable)
- PostgreSQL metadata
- Audit logging (synchronous, append-only)
- Token auth (JWT)
- Basic web UI
- Repository proxying
- NGINX front router in compose

---

# Long-Term Vision

- Artifact repository
- OCI registry
- Software supply chain platform
- Provenance and security platform
- Enterprise package distribution system

A single `docker compose up` should be all it takes to run a production-grade
instance on a single host.
