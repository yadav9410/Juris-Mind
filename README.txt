JurisMind — India Code connectivity and request-budget patch

REPLACE THESE FILES (preserve the paths):
1. backend/app/sources/external_research.py
2. backend/tests/test_external_research.py

WHY THIS PATCH
Render logs show ConnectTimeout to upload.indiacode.nic.in, followed by a frontend 60-second read timeout. The previous patch added the upload host to the allowlist but did not provide an alternate official-host route or sufficiently bound the time spent on failed retrievals.

CHANGES
- Adds the legacy official India Code hosts indiacode.nic.in and www.indiacode.nic.in to the allowlist and Brave domain query.
- Ranks direct legacy India Code PDF/bitstream results ahead of the upload-subdomain viewer result.
- Does not retry ConnectTimeout; uses bounded connect/read timeouts.
- Limits automatic document fetches to two India Code documents and one document per other provider, while retaining all search leads in the response.
- Records explicit source update dates when present. Undated documents are marked freshness_status=not_established; an old dated consolidation is not represented as current.
- Keeps TLS certificate verification enabled and authority verification_status=not_verified.

VALIDATION
- Targeted external-research tests: 26 passed.
- Backend tests suite: 133 passed, 3 skipped.
- Python compilation passed.

IMPORTANT LIMITATION
The legacy India Code PDF endpoint was reachable through external web inspection, but this patch has not been live-tested from the user's Render region. That accessible PDF says "Last Update 18-8-2021". It is suitable for testing retrieval/extraction, but must not be presented as the current consolidated IBC. The result now carries source_update_date and freshness_status so the application can disclose that limitation.

DEPLOYMENT
Replace the two files, commit and push, then redeploy the backend. Re-run the IBC Section 7 test. Check whether the direct www.indiacode.nic.in bitstream result is selected and inspect source_update_date/freshness_status. If the old PDF is returned, treat it as a historical snapshot pending reconciliation with later official amendment Acts, including the 2026 amendment listed by IBBI.
