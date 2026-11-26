# Nyaykosh connector (Release 3)

## What is included

- `app/sources/nyaykosh.py`: read-only HTTP client for Nyaykosh's publicly demonstrated JSON resources.
- `scripts/test_nyaykosh_api.py`: live, read-only smoke test against the published DPDP Act example.
- `tests/test_external_research.py`: mocked contract tests for successful law/penalty responses, invalid slugs and 404 handling.

## Supported endpoint shapes

The Nyaykosh site currently demonstrates these versioned resources:

- `GET https://lawascode.negd.in/v1/laws/{law_id}`
- `GET https://lawascode.negd.in/v1/laws/{law_id}/penalties`

The connector intentionally does not invent a search/list endpoint or undocumented response fields. The published example slug used for the smoke test is `dpdp-2023`.

## Run the live smoke test

From `backend/`:

```bash
python scripts/test_nyaykosh_api.py
```

No Nyaykosh API key is required for public reads. The script prints only a compact response summary (HTTP status, law id/title/section count, penalty count and verification status), not the full statute text.

## Use from Python

```python
from app.sources.nyaykosh import NyaykoshClient

client = NyaykoshClient()
law = client.get_law("dpdp-2023")
combined = client.get_law_with_penalties("dpdp-2023")
```

## Legal provenance safeguards

A successful API response means only that Nyaykosh returned data. The connector sets `verification_status` to `not_independently_verified`. Before using text in a legal memo, cross-check the official Gazette/PDF, commencement status, amendments and the law's temporal applicability. An HTTP 404 for an Act means this endpoint did not return that slug; it is not proof that the Act does not exist in Indian law.

## Current verification result in this build environment

- Automated backend suite: `121 passed, 3 skipped` (`pytest -q tests`).
- Live smoke test attempted: blocked by this environment's outbound DNS/network failure (`ConnectError`).
- The live API response therefore remains unconfirmed here; run the smoke test from Render or a machine with outbound HTTPS access before enabling production ingestion.
