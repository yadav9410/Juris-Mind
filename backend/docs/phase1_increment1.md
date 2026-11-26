# Phase 1 — Increment 1: Backend Foundation

## Scope
This increment creates the API process, configuration, database connection
layer, initial tenant identity tables, health checks, and smoke tests.

## Not included yet
- Supabase JWT verification or login screens
- PostgreSQL row-level security policies
- Neon deployment configuration
- Cloudflare R2 uploads
- PDF extraction or OCR
- Legal-source crawling or ingestion
- Agent orchestration or memo generation

## Acceptance checks
1. The API starts locally with the documented command.
2. `/` and `/health/live` return HTTP 200.
3. `/health/ready` returns HTTP 200 when the configured database is reachable.
4. The test suite passes.
5. No secrets are committed to Git.
6. No private-document endpoint is exposed before tenant authorization exists.
