# Increment 16 — Legal Authority Treatment & Currentness

## Objective

Record later judicial treatment of an identified authority using a traceable
passage from an ingested treating judgment. This increment is a treatment
register, not an automated citator or legal-status engine.

## Supported treatment labels

`followed`, `relied_upon`, `applied`, `approved`, `affirmed`, `distinguished`,
`not_followed`, `disapproved`, `overruled`, `reversed`, `modified`, `questioned`,
`doubted`, `referred`, `stayed`, `set_aside`, `remanded`, `considered`.

These labels describe the relationship asserted by a user/reviewer. They are
not inferred from citation co-occurrence or semantic similarity.

## API

- `POST /research/authority/treatments` — create a treatment assertion.
- `GET /research/authority/treatments/{treatment_id}` — retrieve one record.
- `POST /research/authority/treatments/{treatment_id}/review` — append a review
  decision (`confirmed`, `rejected`, `needs_further_review`). Owner/admin only.
- `GET /research/authority/history?authority_citation=...&tenant_id=...` —
  retrieve the workspace's recorded treatment history for an exact citation
  string (case-insensitive match).

Every treatment must reference an existing `evidence_chunk_id` belonging to
the supplied `treating_job_id`. An optional `evidence_verification_id` must
belong to the same workspace and chunk. A linked verification contributes its
file-integrity status; it does not prove the treatment interpretation.

## Data and security

Migration `0017_authority_treatment` creates:
- `authority_treatments`
- `authority_treatment_reviews`

Both tables have ENABLE/FORCE ROW LEVEL SECURITY and tenant-membership policies
on PostgreSQL. Runtime grants are SELECT/INSERT only. Review decisions are
append-only; later decisions do not erase earlier review events. API writes
flush and serialize before commit to avoid reloading expired ORM instances
outside transaction-local RLS context.

## Currentness limitations

The history endpoint always returns `currentness_assessment: review_required`.
It reports counts of confirmed positive and adverse labels, but does not conclude
that an authority is good law or bad law. A complete currentness assessment
requires at least:
- the exact proposition and ratio being considered;
- court hierarchy and territorial jurisdiction;
- bench strength and binding-precedent rules;
- the procedural posture and operative order;
- later appeals, stays, reversals, modifications and subsequent treatment;
- completeness and authenticity of the sources reviewed.

Absence of a treatment record is not evidence that no later treatment exists.
A file hash establishes byte-level integrity against the repository's ingestion
record, not court/publisher authenticity.

## Suggested test workflow

1. Ingest a later judgment.
2. Use `/search/hybrid` to find a passage in that judgment that expressly treats
   an earlier authority.
3. Copy the actual `job_id` and `chunk_id` from the search result.
4. Create a treatment assertion with the earlier authority's citation and the
   exact scope/proposition said to be treated.
5. Have a workspace owner/admin record a review decision after examining the
   full judgment context.
6. Retrieve the individual treatment and its authority history.

No new LLM inference is used in this increment. No treatment is auto-generated.
