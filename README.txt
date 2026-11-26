JurisMind targeted official-source retrieval patch

Replace these files, preserving the paths:

1) backend/app/sources/external_research.py
2) frontend/app.py
3) backend/tests/test_external_research.py

What changed:
- Long memo instructions are reduced to short issue-specific Brave queries (max 220 chars before site filters; max 300 chars sent as q).
- Brave provider errors now retain HTTP status, response detail, failure category, and the actual query sent.
- Search results distinguish completed, partial, provider_error, and no_results.
- Per-source summaries expose search_status and search_errors.
- Frontend displays provider-level status and errors rather than always reporting that search finished successfully.
- HTTP 429 retrieval failures are explicitly categorized; existing host cooldown and TLS verification remain enabled.
- Added tests for concise query generation, Brave HTTP 422 diagnostics, and partial provider success.

Validation performed:
- backend/tests/test_external_research.py: 17 passed
- backend/tests/: 124 passed, 3 skipped
- Python compilation of frontend/app.py and external_research.py passed.

Not included / not claimed:
- This does not guarantee that Brave will return relevant official judgments.
- This does not bypass CAPTCHA or court access controls.
- It does not implement legal-authority verification; verified_authorities_count remains 0 unless a separate verification process is implemented.
- A live Brave or court-portal test was not possible in this environment. After deployment, inspect per-source status and query_sent fields.
