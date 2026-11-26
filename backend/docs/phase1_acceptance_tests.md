# Phase 1 Acceptance Tests

1. A request can represent an India + Uttar Pradesh research question and an explicit as-of date.
2. A request can carry multiple legal domains without assuming a single domain.
3. The system distinguishes legislation, judgments, gazette notifications, court records, secondary research and user documents.
4. A source record can preserve URL, publisher, jurisdiction, publication/effective dates, retrieval time, version, page/paragraph/section and checksum.
5. A legal claim can be linked to one or more source IDs.
6. Citation identity, pinpoint and support statuses are separate fields.
7. A memo defaults to a lawyer-review draft and can expose assumptions, missing facts and limitations.
8. The source registry labels source tiers but does not claim that a portal has an API.
9. Threat model covers tenant isolation, private uploads, prompt injection, logging, exports and deletion.
10. Tests run locally with `pytest`.
