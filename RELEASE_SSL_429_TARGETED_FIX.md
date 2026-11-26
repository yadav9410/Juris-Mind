# JurisMind SSL and HTTP 429 Targeted Fix

Baseline: the immediately preceding Official Source Reliability Patch project.

## e-Gazette TLS
- Added an explicit `certifi` dependency and configure HTTPX with a verified SSL context using the Mozilla CA bundle.
- Certificate verification and hostname verification remain enabled (`CERT_REQUIRED`, `check_hostname=True`).
- No `verify=False`, insecure fallback, or certificate-validation bypass is used.
- If the portal serves an incomplete or invalid certificate chain, retrieval will continue to fail safely and the logs will preserve the TLS failure detail. This requires a live Render test.

## Allahabad High Court HTTP 429
- Increased per-host pacing to one request every 12 seconds for eLegalix.
- Added a process-wide per-host cooldown after HTTP 429: use the portal's `Retry-After` value when supplied; otherwise default to 15 minutes for eLegalix.
- Requests arriving during cooldown are suppressed locally and reported as HTTP 429 cooldown results instead of hitting the portal again.
- No immediate retry is performed after 429; no CAPTCHA or access-control bypass is attempted.

## Dependencies and persistence
- Added `certifi>=2025.1.31,<2027` to backend requirements.
- No database migration and no new secret are required.
- Existing Brave API key remains unchanged.
- Rate-limit state is process-local. Multiple Render instances do not share cooldown state; a shared Redis limiter would be required for multi-instance coordination.

## Validation
- Full backend test suite: 118 passed, 3 skipped.
- Frontend and modified backend Python compilation: passed.
- ZIP integrity: passed.
- Live e-Gazette certificate-chain and eLegalix rate-limit behavior must be verified after deployment from Render.
