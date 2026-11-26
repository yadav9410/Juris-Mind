JurisMind — India Code document-selection and diagnostics patch

REPLACE THESE FILES (preserve the paths):
1. backend/app/sources/external_research.py
2. backend/tests/test_external_research.py

ROOT CAUSE ADDRESSED
India Code publishes official Act PDFs on upload.indiacode.nic.in as well as pages on indiancode.gov.in. The previous allowlist omitted upload.indiacode.nic.in, so direct official PDF search results were discarded. In addition, the fetcher only attempted embedded document links when the landing-page HTML looked too short. India Code landing pages can contain enough metadata/navigation text to pass that threshold while still not being the Act text.

CHANGES
- Adds upload.indiacode.nic.in to the explicit India Code official-host allowlist and Brave site query.
- For India Code HTML pages, prefers a same-host/allowlisted embedded Act PDF when a document link is present, even if the landing page contains substantial boilerplate text.
- Adds structured diagnostic logs for final URL, HTTP status, content type, bytes, embedded candidates, PDF page count, extracted character counts, per-page text lengths, OCR usage, and extraction failure reason.
- Does not disable TLS verification, bypass access controls, or mark authorities verified.
- Keeps original landing-page URL and actual PDF URL separately in result metadata.

VALIDATION
The tests cover the upload subdomain allowlist and confirm that an embedded official PDF is selected even when the HTML landing page contains enough generic text to pass the old threshold.

LIMITATION
This patch has not been tested against the user's live Render environment. After deployment, inspect the new log lines beginning "Official HTML inspected", "India Code embedded document selected", and "Official PDF extraction summary". The logs will now identify the exact document URL and extraction result without logging full statutory text.
