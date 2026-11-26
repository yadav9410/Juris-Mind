# External Research Hotfix

This hotfix is based on the latest uploaded Juris-Mind-main project ZIP.

## Changes
- Fixed duplicate Streamlit widget keys in external official-source results. Keys now include a per-result index and a stable digest of the result identity, so identical document hashes cannot collide.
- Added a unique key to each external-source link button.
- Added backend logging for Brave search start, HTTP response status, returned hit counts, official-document fetch status/content type/size, retrieval success/failure, and final totals.
- Logs do not include the Brave API token.
- Corrected whitespace normalization in external queries and newline joining in extracted PDF text.

## Configuration
Keep `BRAVE_SEARCH_API_KEY` configured only in the Render backend environment. No frontend key and no database migration are required.

## Validation
- Backend tests: 112 passed, 3 skipped.
- Python compilation: frontend and modified backend modules passed.
- Live Brave authentication and live portal retrieval must still be confirmed from Render logs after deployment.
