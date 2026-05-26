**CLAUDE.md:**

```markdown
# CLAUDE.md

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
- Object storage
- Redis (metadata caching only — scope limited to cache)
- Search/index backend

This allows:
- Horizontal scaling
- HA deployments
- Easier upgrades

---

## 3. Storage backend
Artifacts are immutable blobs.

Support:
- Filesystem backend (priority 0 — local dev and on-prem deployments)
- S3-compatible (priority 2 — on-prem first: Ceph RadosGW, etc; cloud secondary)

Both backends sit behind the same interface. The platform does not bundle or manage
storage infrastructure.

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
YAML file, with env taking precedence. Hot reload where reasonable.

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
- Secret handling hygiene

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

Primary: single-node Docker Compose on bare metal or VM.
Target platform: RHEL/Rocky/AlmaLinux/OracleLinux.

NGINX sits at the front, terminating HTTP and routing to the server container.

```
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
                        │  server ──▶ Storage backend          │
                        │             (fs or S3-compatible)    │
                        └─────────────────────────────────────┘
```

NGINX handles:
- TLS termination (certs mounted as volumes)
- Reverse proxy to API server and web UI
- Streaming passthrough for large uploads (client_max_body_size 0)

The server container is stateless. All persistent state is in PostgreSQL,
Redis (cache only), and the configured storage backend.

Deployment: `docker compose up -d`
Upgrades: `docker compose pull && docker compose up -d`

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
- Storage abstraction (filesystem or S3)

---

### Index/Search Service
- Metadata indexing
- Full-text search (PostgreSQL FTS at MVP)
- Tag/version lookup

Post-MVP search backend options: OpenSearch, Bleve.
Primary package format: RPM.

---

### Auth Service
- Local users
- Token issuance
- Service accounts
- JWT validation (centralized, HS256)

Future: OIDC, LDAP, SAML — designed for via interfaces, not implemented at MVP.
No external auth platform dependencies (no Ory, Zitadel, Dex, Keycloak).

---

### Background Workers
- Garbage collection
- Retention enforcement
- Indexing
- Scheduled metadata syncs (yum/apt)
- Replication (post-MVP)
- Vulnerability scanning (post-MVP)

Runs as a separate container in compose using the same image, different command.

---

### Event Bus
Internal async event system. Evaluate carefully — operational complexity must be justified.

Candidates:
- Redis Streams (preferred — already a compose dependency)
- NATS (evaluate if Redis Streams proves insufficient)
- Kafka (avoid unless there is a concrete forcing reason)

Used for: indexing triggers, notifications, webhook delivery (post-MVP).

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
Artifacts keyed by content hash:

```
sha256/ab/cd/<full-digest>
```

- Integrity verification: configurable, can be disabled
- Garbage collection: platform tracks references, removes unreferenced blobs
- Deduplication: not a platform concern — handled at storage layer if at all

---

# Tech Stack

## Language
Go 1.22+

## HTTP
TBD — chi or echo. No magic. NGINX handles TLS and edge routing.

## Database
PostgreSQL 16. Driver: pgx. Query layer: evaluate sqlc (type-safe generated queries,
no ORM magic) vs raw pgx. Migrations: goose. No implicit eager loading, no hidden behavior.

## Storage
- Filesystem: local disk, path-based
- S3-compatible: aws-sdk-go-v2 against any S3-compatible endpoint (Ceph, MinIO, AWS).
  On-prem first. All config via environment.

## Cache / Event Bus
Redis 7. Cache only at MVP. Redis Streams for internal async if needed.

## Auth
Internal JWT (HS256). No external auth platform at MVP. Auth interfaces designed
for future OIDC/LDAP/SAML without a rewrite.

## Observability
Not an MVP priority. slog for structured logging throughout.

Post-MVP: Prometheus metrics, OpenTelemetry tracing.

## Frontend
TBD — SvelteKit or React. API-driven only, RBAC-aware, repository browsing,
upload UX, audit visibility.

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

# OCI Registry Support

First-class OCI support is mandatory. The OCI spec is the foundation; Docker image
format is a specific manifest schema on top of it — they share the same registry protocol.

Support:
- OCI artifacts (primary)
- Docker images (OCI-compatible manifest v2)
- Helm OCI, WASM OCI, SBOM OCI, signatures/attestations: post-MVP, deprioritized

---

# Performance

- Streaming uploads/downloads — no full blob loads into memory
- No temp disk copies where avoidable
- Cursor-based pagination throughout
- No N+1 queries
- Prefer zero-copy patterns where feasible

---

# API Design

## Versioning
```
/api/v1/
```

## Pagination
Cursor-based only. No offset pagination.

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

# Database Guidelines

## Migrations
goose. Deterministic and reversible where practical.

## Query Design
- Explicit joins
- Cursor-based pagination
- No N+1 queries
- No implicit ORM behavior

---

# Operational Requirements

## Deployment
Single-node Docker Compose on RHEL-family bare metal or VM.
Kubernetes and cloud deployments are not a current target but the stateless
architecture does not preclude them later.

## Upgrades
```
docker compose pull
docker compose up -d
```

Migrations run as a dedicated compose service that completes before the server starts.

## Backup
- PostgreSQL: pg_dump on a schedule
- Storage: operator responsibility
- Secrets: never in the repo

---

# Security

## Secrets
Passed via environment variables or Docker secrets. Never in committed config files.

## Input Validation
All uploads validate: size, checksum, content type, path normalization.

## Supply Chain (post-MVP)
Cosign, Sigstore, in-toto attestations, SBOM ingestion.

---

# Code Layout

```
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
    /fs
    /s3
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
```

Small, focused interfaces. No god interfaces.

---

# Testing

- Unit tests
- Integration tests (containerized preferred)
- API tests

---

# Non-Goals (MVP)

- Kubernetes / Swarm
- External auth platforms
- Replication
- Vulnerability scanning
- Advanced search (beyond PG FTS)
- Group repositories (validate need before investing)
- Observability stack
- Multi-region / multi-node HA
- RPM packaging

---

# MVP Scope

- Hosted repositories: Maven, PyPI, Generic blob
- OCI registry support
- RBAC + local users + service accounts
- Filesystem and S3 storage backends (No?)
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

A single `docker compose up` on a RHEL-family host should be all it takes to run
a production-grade instance.
```