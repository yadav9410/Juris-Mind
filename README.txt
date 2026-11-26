JurisMind — India Code extraction patch

REPLACE THESE FILES (preserve the paths):
1. backend/app/sources/external_research.py
2. backend/tests/test_external_research.py

WHAT THIS PATCH CHANGES
- India Code HTML landing/viewer pages are inspected for embedded same-host PDF/bitstream links.
- If the landing page contains only a viewer shell (for example, a page number such as "1"), the connector attempts to retrieve the embedded official document.
- PDF extraction now rejects tiny text layers rather than counting a page number as extracted legal text.
- If Tesseract is installed in the runtime, low-text PDF pages receive an OCR attempt. If OCR is unavailable or unsuccessful, the extraction failure is made explicit; TLS verification is not disabled.
- Extracted text is retained up to 50,000 characters, and a requested numbered statutory section (for example Section 7) is separately captured up to the next numbered section heading, preserving subsection text.
- Result metadata includes extraction_quality, ocr_used, embedded_document_url, targeted_provisions and targeted_provision_status.

VALIDATION PERFORMED
- backend/tests/test_external_research.py: 20 passed
- backend/tests/: 127 passed, 3 skipped
- Python compilation: passed

IMPORTANT LIMITATIONS
- Tests use mocked HTTP/PDF responses. A live India Code/Render test has not been performed from this environment.
- If the India Code PDF is image-only and Tesseract is not installed on Render, the connector will correctly report insufficient text rather than claim extraction succeeded. OCR deployment would require adding/installing Tesseract in the Render runtime.
- Section extraction depends on the source PDF's numbered heading being text-extractable and recognizable. Review the returned source text and targeted_provisions before relying on it.
- This patch does not verify the current legal status, amendments, commencement or proposition-level authority.
