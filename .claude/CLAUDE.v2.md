Looking at your comments, here's the cleaned-up version:

---

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

This project is NOT intended to be a Nexus clone. It should modernize the architecture and UX while supporting common enterprise artifact workflows.

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
- Redis (metadata caching — TBD, scope limited to cache only)
- Search/index backend

This allows:
- Horizontal scaling
- HA deployments
- Easier upgrades

---

## 3. Flexible storage backend
Artifacts are immutable blobs.

Support:
- S3-compatible (on-prem first; cloud secondary)
- Filesystem backend

---

## 4. Immutable-by-default artifacts
Published artifacts should generally be immutable.

Allow configurable policies:
- immutable
- overwrite
- append-only
- retention-based

Configurable audit on mutation events.

---

## 5. Global scope to simplify operations

---

## 6. Security is an architectural concern

Required (MVP):
- RBAC
- Token management
- Audit logging

Future:
- OIDC/SAML support
- Signed artifacts
- Provenance metadata
- SBOM support
- Secret handling hygiene

---

## 7. Modular repository engines
Repository formats implemented as isolated modules.

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

Metadata sync should be implemented where feasible (e.g. rpm/apt repo metadata).

---

# High-Level Architecture

## Components

### API
Responsibilities:
- Authentication
- Authorization
- Routing
- Request validation
- Metrics

---

### Repository Service
Handles:
- Artifact upload/download
- Metadata
- Repository rules
- Retention policies
- Storage abstraction

---

### Index/Search Service
Handles:
- Metadata indexing
- Full-text search
- Dependency graph search
- Tag/version lookup

Potential backends:
- PostgreSQL FTS
- OpenSearch
- Bleve

Prefer FOSS solutions. Primary package format: RPM. Primary target platform: RHEL/Rocky/AlmaLinux/OracleLinux.

---

### Auth Service
Responsibilities:
- Local users
- Token issuance
- Service accounts
- Future: OIDC, LDAP, SAML

No external auth platform dependencies at MVP. JWT validation centralized internally.

---

### Background Workers
Handles:
- Cleanup
- Garbage collection
- Replication (post-MVP)
- Indexing
- Vulnerability scanning (post-MVP)
- Retention enforcement
- Scheduled syncs on applicable repos

---

### Event Bus
Internal async event system. **Evaluate carefully — operational complexity must be justified.**

Candidates:
- Redis Streams (preferred if Redis is already a dependency)
- NATS (evaluate if Redis Streams proves insufficient)
- Kafka (avoid unless there's a concrete reason)

Used for:
- Indexing
- Notifications
- Webhook delivery

Audit fanout should NOT go through the event bus — audit writes should be synchronous and durable.

---

# Storage Model

## Metadata
Primary database: PostgreSQL

Relational data for:
- Repositories
- Permissions
- Users
- Artifact metadata and manifests

Audit records: stored in PostgreSQL but as append-only records, NOT via event bus fanout.

Do NOT store blobs in PostgreSQL.

---

## Blob Storage
Artifacts stored by content hash:

```text
sha256/ab/cd/<digest>
```

Features:
- Integrity verification (configurable, can be disabled)
- Garbage collection
- Deduplication: not a platform-level concern — enterprise deployments typically handle this at the SAN/storage layer

---

# Core Features

## Repository Types

### Hosted
Internal artifact hosting.

### Proxy
Cache upstream repositories.

### Group
Aggregate multiple repositories into a virtual endpoint. **Low priority — validate need before investing here.**

---

## OCI Registry Support

First-class OCI support is mandatory. The OCI spec is the foundation; Docker image format is a specific manifest schema on top of it — they share the same registry protocol.

Support:
- OCI artifacts (primary)
- Docker images (OCI-compatible manifest v2)
- Helm OCI, WASM OCI, SBOM OCI, signatures/attestations: post-MVP, deprioritized

---

## Replication
**Not in MVP scope.**

Post-MVP modes:
- Push
- Pull
- Scheduled

---

## Search
**Not in MVP scope.**

Post-MVP:
- Artifact name, version, tags, checksums, metadata, labels

---

## Audit Logging

Audit ALL:
- Logins
- Token operations
- Artifact mutations
- Permission changes
- Admin actions

Audit logs must be append-only and tamper-resistant. Written synchronously to PostgreSQL.

---

# Tech Stack

## Language
Go

---

## HTTP
TBD. Candidates: chi, echo, fiber. Avoid overly magical frameworks. NGINX as a reverse proxy/routing layer is worth evaluating (controller→worker pattern, per-repo virtual servers).

---

## Database
PostgreSQL

Driver: pgx

Query layer: TBD — evaluate sqlc (type-safe generated queries, low magic) vs raw pgx. Avoid heavy ORM abstraction. No implicit eager loading, no hidden behavior.

---

## Object Storage
S3-compatible API abstraction. On-prem first (MinIO, Ceph, etc). Use `aws-sdk-go-v2` — it works against any S3-compatible endpoint.

---

## Auth
No external auth platform at MVP (no Ory, Zitadel, Dex, or Keycloak dependency). Implement local users, service accounts, and JWT issuance internally. Design auth interfaces so OIDC/LDAP/SAML can be added later without a rewrite.

---

## Messaging
Redis Streams if an event bus is needed — avoids introducing a new infrastructure dependency. Revisit NATS if Redis Streams proves limiting.

---

## Observability
Not an MVP priority.

Post-MVP:
- Prometheus metrics
- OpenTelemetry tracing
- Structured logging (slog)

---

## Frontend
TBD: React, SvelteKit, or Vue.

Requirements:
- API-driven only
- RBAC-aware
- Repository browsing
- Upload UX
- Audit visibility

---

# Repository Engine Guidelines

Each repository type exposes:
- Upload handlers
- Download handlers
- Metadata extraction
- Indexing logic
- Validation logic
- Retention hooks

Engines are isolated behind interfaces. No global repository-type conditionals. No giant switch statements.

---

# Performance Requirements

- High concurrency
- Large artifact support
- Streaming uploads/downloads
- No full blob loads into memory
- Avoid temp disk copies where possible
- Prefer streaming pipelines and zero-copy patterns

---

# Database Guidelines

## Migrations
Use goose or atlas. Migrations must be deterministic and reversible where practical.

## Query Design
- Explicit joins
- Cursor-based pagination
- No N+1 queries
- No implicit ORM behavior

---

# API Design

## Versioning
```
/api/v1/
```

## Pagination
Cursor-based, not offset.

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

## Deployment Targets
- Kubernetes
- Docker Compose
- Bare metal / VM

## HA
- Multiple API nodes
- Rolling upgrades
- Shared object storage + shared database
- No node-local critical state

## Backup
- PostgreSQL
- Object storage
- Config/secrets

Document restore procedures early.

---

# Security Requirements

## Secrets
Never store plaintext. Use envelope encryption; KMS integration where environment supports it.

## Supply Chain (post-MVP)
- Cosign / Sigstore
- in-toto attestations
- SBOM ingestion

## Input Validation
All uploads validate:
- Size
- Checksum
- Content type
- Path normalization

---

# Code Organization

```text
/internal
  /api
  /auth
  /storage
  /repo
  /search
  /workers
  /events
/pkg
/cmd
/web
```

Small, focused interfaces. No god interfaces.

---

# Testing

- Unit tests
- Integration tests (containerized preferred)
- API tests

---

# Configuration

- YAML with env overrides
- Hot reload where reasonable

---

# Non-Goals (Initial Phase)

- Distributed SQL
- Multi-region active-active
- Blockchain anything
- Custom storage engine
- Excessive microservice fragmentation

---

# MVP Scope

- Hosted repositories (Maven, PyPI, Generic blob)
- OCI registry support
- RBAC
- S3 backend
- PostgreSQL metadata
- Audit logging
- Token auth
- Basic web UI
- Repository proxying

Explicitly out of MVP: replication, vulnerability scanning, advanced search, group repositories, external auth platforms, observability stack.

---

# Long-Term Vision

Evolve into:
- Artifact repository
- OCI registry
- Software supply chain platform
- Provenance and security platform
- Enterprise package distribution system

While remaining operationally lightweight compared to legacy enterprise artifact managers.