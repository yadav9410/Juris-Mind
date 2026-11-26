JurisMind targeted replacement patch

Replace these files in your repository (preserve the folder paths):

1) backend/app/sources/external_research.py
2) backend/tests/test_external_research.py

What this patch changes:
- Rejects obvious CAPTCHA, login, access-denied, generic portal/homepage responses.
- Requires conservative source-specific content markers before an HTML/PDF extraction is counted as a legal document.
- Keeps downloaded count separate from identified-document/extracted count.
- Preserves verification_status=not_verified. This patch does NOT claim legal authority verification.

Validation run:
  pytest -q tests
Result in the supplied project copy: 124 passed, 3 skipped.

Important scope note:
- This patch addresses false-positive document extraction in the official-source retrieval pipeline.
- It does not yet wire the standalone NyayKosh client into the research orchestrator or add NyayKosh to the frontend source controls. Do not assume NyayKosh appears in the live research workflow after applying only these two replacements.
- No database migration or environment-variable change is required for these two files.
