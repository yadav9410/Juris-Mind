# Increment 17 — Statutory Versioning & Temporal Law

## Purpose

Preserve statutory provision text by effective period and retrieve the recorded
version applicable on a legally relevant date. The shared statutory corpus is
distinct from tenant-private workspace documents.

## Data model

- `statutory_instruments`: Act, rules, regulations, notification, ordinance or
  other instrument identity; canonical identifier, jurisdiction, enactment and
  publication dates.
- `statutory_provisions`: stable provision reference such as Section 3(2).
- `statutory_versions`: captured provision text, effective interval,
  commencement/publication dates, source job/chunk and optional evidence
  verification.
- `statutory_events`: enacted, published, commenced, amended, inserted,
  substituted, omitted, repealed, expired, repeal/savings or corrected event,
  with date, description and source evidence.

Versions are retained as separate records. There is no endpoint to overwrite or
delete captured text. An open-ended version may be closed once by setting its
exclusive end date; this changes temporal metadata only and records who closed it.

## Temporal convention

Effective intervals are half-open: `[effective_from, effective_to)`.
`effective_from` is inclusive; `effective_to` is exclusive. A null end date means
the recorded version has no known end date in the repository. Overlapping
intervals for one provision are rejected. Close an earlier interval before
adding its successor.

The API keeps enactment, publication, commencement and effective dates as
separate fields. It does not infer one from another. The data-entry operator
must use the legally supported commencement/effective date, including
provision-specific commencement where applicable.

## API

- `POST /research/statutes/instruments` — create an instrument.
- `GET /research/statutes/instruments?q=...` — list/search instruments.
- `POST /research/statutes/instruments/{instrument_id}/provisions` — create a
  stable provision record.
- `POST /research/statutes/provisions/{provision_id}/versions` — add an
  effective-dated text version.
- `POST /research/statutes/versions/{version_id}/close` — close a previously
  open-ended version by setting its exclusive end date; captured text remains unchanged.
- `POST /research/statutes/provisions/{provision_id}/events` — record a
  dated statutory event.
- `GET /research/statutes/provisions/{provision_id}/as-of?date=YYYY-MM-DD` —
  resolve the repository's recorded text for a date.

## Evidence and roles

Each version/event must cite a real ingestion job and chunk belonging to that
job. Optional evidence-verification IDs must match the same source job/chunk.
The corpus is shared across provisioned workspaces. Authenticated workspace
members can read it; only owners/admins can create instruments, provisions,
versions and events. PostgreSQL RLS policies enforce the same broad distinction
for the runtime role.

An evidence-verification record marked matched supports file-integrity linkage;
it does not independently authenticate the publisher or establish the legal
effect of an amendment.

## Lookup statuses

- `complete`: exactly one version covers the requested date and its linked
  evidence verification has `integrity_status=matched`.
- `partial`: exactly one recorded version covers the date but independent
  integrity verification is absent or not matched.
- `unresolved`: no version covers the date, or multiple versions cover it.

These labels describe repository coverage only. `unresolved` does not mean the
law did not exist. `partial` does not mean the text is legally inapplicable.
No automated legal conclusion is made.

## Suggested test workflow

1. Ingest an official Act/amending Act and identify the exact provision chunk.
2. Create the statutory instrument.
3. Create the provision identity.
4. Add the text version with effective-from/to, commencement and publication
   dates separately.
5. Link an Increment 15 evidence-verification record when available.
6. Record amendment/commencement events with their own source passage.
7. Query the provision using the date relevant to the legal issue.

Do not enter a historical version from an unverified search snippet. Inspect the
official instrument, amendment text, commencement notification and any
provision-specific commencement rules first.
