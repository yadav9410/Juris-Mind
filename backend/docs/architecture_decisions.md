# Architecture Decisions — Phase 1

## AD-001: Broad legal intake, staged evidence depth
The product accepts questions across legal domains. Retrieval depth and evaluation datasets expand incrementally; broad domain support must not be misrepresented as equal source coverage.

## AD-002: Initial jurisdiction
India-wide central law plus Uttar Pradesh state materials and relevant courts. Jurisdiction is explicit request data and may require clarification.

## AD-003: Multi-user from day one
All private records and files are owner- and tenant-scoped. The database schema and APIs must enforce authorization server-side, not rely on UI filtering.

## AD-004: Public-source-first
No paid legal database is required for MVP. Primary official sources are preferred; secondary discovery sources are clearly labelled and used subject to terms.

## AD-005: Hybrid verification
LLMs assist interpretation; deterministic services check identifiers, locations and provenance. Claim support and legal status may still require human review.

## AD-006: Cloud portable
Dockerized Streamlit and FastAPI, PostgreSQL/pgvector, and private object storage. Hosting provider is deferred until region, data residency, cost and operational needs are confirmed.

## AD-007: User files are untrusted
Uploaded documents are evidence, not instructions. No client-confidential uploads before security release gates pass.

## AD-008: Separate legal work, source document, and captured version
A legal work (the underlying Act, rule, notification, or judgment) is distinct from a source document that publishes it, and from each captured version of that document. This preserves provenance and permits multiple captures without overwriting prior evidence.

## AD-009: Preserve legal time and repository time separately
Publication date, legal validity dates, and repository capture time are separate fields. Unknown dates remain null; the system must not infer commencement from publication date.

## AD-010: Schema changes use Alembic migrations
Database schema changes are version-controlled migrations. `Base.metadata.create_all()` is suitable for isolated tests, not as the production schema deployment process.
