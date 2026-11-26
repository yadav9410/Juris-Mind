# JurisMind — Official Source Reliability Patch

Baseline: latest uploaded `Juris-Mind-main.zip`.

## Changes
1. e-Gazette connectivity diagnostics now log the host, exception type, and bounded error detail for connection and timeout failures. A single bounded retry is used for transient connection failures; the code does not claim to fix external DNS/TLS/network reachability.
2. Allahabad High Court/e-Gazette requests are paced per host within a backend process. HTTP 429 is not immediately retried; status and Retry-After are logged so the portal's limit is respected.
3. Successful official-document fetches are cached in-process for six hours to avoid repeat downloads within the same running instance.
4. Same-host HTTPS redirects are checked against the existing official-host allowlist; redirects to non-allowlisted hosts are rejected.
5. Brave queries are tailored by source category (legislation, Gazette, Supreme Court judgments, Allahabad High Court judgments), while retaining the user's original legal issue and optional jurisdiction/court.
6. API response counters separately report search results, downloaded documents, extracted documents, failed retrievals, and verified authorities. `document_count` remains as a backward-compatible alias for downloaded documents.
7. Per-source summaries are returned and displayed in the frontend.
8. Added regression tests for query tailoring, retrieval accounting, and HTTP 429 failure reporting.

## Important limitations
- Rate limiting and cache are process-local, not shared across multiple Render instances or worker processes. A shared Redis limiter/cache would be needed for multi-instance coordination.
- e-Gazette `ConnectError` can still occur if Render cannot reach the host due to DNS, TLS, network policy, or the portal's infrastructure. This patch improves diagnosis and bounded retry; it cannot override external network failures.
- HTTP 429 is reported and not hammered with retries. A subsequent user-initiated search after the portal's limit window may succeed.
- Search/download/extraction are not legal authority or proposition verification. `verified_authorities_count` remains zero.

## Configuration / deployment
- Keep existing `BRAVE_SEARCH_API_KEY` in the backend environment.
- No new environment variable or database migration is required.
- Replace repository files with this ZIP and deploy backend and frontend.
