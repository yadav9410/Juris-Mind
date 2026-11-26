# JurisMind Release 2 — External official-source research

## What this patch implements

- Curated official-first source registry for India Code, e-Gazette of India, Supreme Court Reports (SCR), Allahabad High Court eLegalix (Allahabad and Lucknow Bench), and the e-Committee Judgments and Orders Search Portal.
- Authenticated workspace-scoped endpoints: `GET /research/sources?tenant_id=...` and `POST /research/discover/official`.
- A transparent discovery plan that returns the official portal entry points and the exact query to run. It explicitly reports `manual_search_required`; it does not fabricate search hits or claim that portals have been searched.
- Updated HTTPS allowlist and safer URL validation in the existing public-source fetcher. Redirects outside the official allowlist and oversized responses are rejected.
- Fix to the research worker loop: `claim_next_job()` returns a `ResearchJob`, so the worker now passes its `.id` to `execute_job()`.

## What this patch deliberately does not claim

This is the external-source integration foundation, not a completed automated web-search agent. Current official portals expose differing interfaces; the e-Committee portal presents CAPTCHA, and the official India Code portal has recently migrated. No CAPTCHA bypass, undocumented endpoint assumption, or automated crawling is introduced. No external authority is silently marked verified or published into the internal corpus.

## Recommended implementation sequence

1. **Release 2A (this patch):** official source registry, authenticated discovery plan, source provenance boundaries, connector host controls, worker fix.
2. **Release 2B:** implement and test portal-specific search adapters only where a stable public interface/API and permitted access are confirmed. Start with India Code/e-Gazette. For judgment search, use the SCR and eLegalix official portals; where CAPTCHA or interactive controls intervene, require a user-mediated search/download.
3. **Release 2C:** add a durable external-document staging record and fetch/import workflow. Preserve source URL, source ID, retrieval timestamp, content hash, content type, publication/citation metadata, and access method. Keep imported documents `authority_verified=false` and `metadata_review_status=pending` until source and authority review.
4. **Release 2D:** merge external and internal candidates in the research job, deduplicate by canonical URL/content hash/citation, retrieve full text, resolve applicable statutory version, and verify proposition-to-pinpoint support. Search snippets remain discovery-only.

## Required evidence/provenance fields for the next phase

`source_id`, `source_tier`, `source_url`, `canonical_url`, `retrieved_at`, `published_at` (when available), `content_sha256`, `access_method`, `document_type`, `court`, `case_number`, `neutral_citation`, `bench`, `judgment_date`, `paragraph/page locator`, `verification_status`, and `verification_evidence`. Missing values must remain null/unknown rather than inferred.

## Deployment

No database migration is required for this patch. Deploy the backend code, then verify the two endpoints using an authenticated workspace owner/member token. Run the backend tests before pushing. Do not change production database credentials or grant additional database privileges for this patch.
