# Increment 17 Release Notes

## Added
- Shared statutory instrument register.
- Stable statutory provision identities.
- Separate, effective-dated statutory text versions.
- Distinct enactment, publication, commencement and effective dates.
- Evidence-linked amendment and commencement event register.
- Source job/chunk validation and optional matching evidence verification.
- Date-based historical provision lookup.
- Half-open temporal intervals and overlap rejection.
- Workspace-member read access and owner/admin write access, with PostgreSQL RLS.

## Migration
- Revision: `0018_statutory_temporal`
- Parent: `0017_authority_treatment`
- Creates `statutory_instruments`, `statutory_provisions`,
  `statutory_versions`, and `statutory_events`.

## API
- `POST /research/statutes/instruments`
- `GET /research/statutes/instruments`
- `POST /research/statutes/instruments/{instrument_id}/provisions`
- `POST /research/statutes/provisions/{provision_id}/versions`
- `POST /research/statutes/versions/{version_id}/close`
- `POST /research/statutes/provisions/{provision_id}/events`
- `GET /research/statutes/provisions/{provision_id}/as-of`

## Automated validation
- Full suite: 86 passed, 3 skipped.
- Changed Python modules compiled.
- Migration head and ZIP integrity checked in build environment.

## Not performed
- No migration against the user's live Neon database.
- No live Supabase-authenticated API test.
- No independent verification of any Indian statute or amendment.
- No automated interpretation of commencement clauses or repeal/savings provisions.
