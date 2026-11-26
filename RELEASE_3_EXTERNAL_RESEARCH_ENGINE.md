# JurisMind — External official-source research engine

## What changed

- Added a real external search adapter using the Brave Search API, restricted to official Indian legal-source domains.
- Added direct retrieval for accessible official HTML and PDF documents.
- PDF text is extracted page-by-page; HTML text is extracted from the original official page.
- Captures source URL, retrieval time, content SHA-256, content type, page previews, and access method.
- All results remain `not_verified`; a search snippet alone is never treated as documentary evidence.
- Research jobs now run external official-source discovery alongside internal corpus retrieval and persist both result sets in the job result JSON.
- Added `POST /research/search/official` for the frontend and changed the Legal Research panel from manual search-plan preparation to actual external search and document retrieval.
- Existing `/research/discover/official` remains available as a manual fallback.

## Required production configuration

Set this environment variable on the backend service:

`BRAVE_SEARCH_API_KEY`

Create a Brave Search API subscription/key and store the key only in the Render backend environment. Do not put it in Streamlit secrets exposed to the browser, frontend source, or Git repository.

If the key is absent, the API returns HTTP 503 and background research jobs explicitly record `external_search_status: not_configured`. JurisMind must not claim that external search ran.

## Official-source and access boundaries

Searches are constrained to:
- India Code: `indiacode.gov.in`
- e-Gazette: `egazette.gov.in`
- Supreme Court Reports: `scr.sci.gov.in`, `sci.gov.in`
- Allahabad High Court eLegalix: `elegalix.allahabadhighcourt.in`

The e-Committee CAPTCHA portal is not automated. Results outside the configured official hosts are discarded. Redirects outside the relevant source allowlist are rejected. This patch does not bypass CAPTCHA, login, paywalls, or other access controls.

The search provider is a third-party index; the legal document itself is fetched directly from the allow-listed official host. A search result that cannot be fetched remains a search lead, not a retrieved authority.

## Verification boundary

`document_retrieved` means an official-host HTML/PDF response was fetched and text was extracted. It does not mean:
- the document is the latest/current version;
- the document is authentic beyond its official-host provenance;
- a case is still good law;
- a cited paragraph supports a proposition.

Those checks require the separate citation, temporal-law, authority-treatment, and proposition-evidence verification stages.

## Deploy

No database migration is required. Add `BRAVE_SEARCH_API_KEY` to the Render backend environment, deploy the backend and frontend, and test `/research/search/official` with an authenticated workspace user.
