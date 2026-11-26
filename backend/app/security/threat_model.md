# Initial Threat Model — Multi-user Legal Research

## Assets
- User identity and organization membership.
- Uploaded contracts, notices, judgments and client documents.
- Research questions, extracted facts, drafts and final memos.
- API keys, database credentials, storage credentials and trace data.

## Trust boundaries
- Browser / Streamlit session to backend API.
- One user or organization to another.
- Backend to database and object storage.
- LLM provider and external legal-source websites.
- Uploaded file content and retrieved web content to agent instructions.

## Threats and required controls
| Threat | Required control |
|---|---|
| Cross-user / cross-tenant data access | Server-side authorization on every object; tenant_id ownership checks; database row-level security where appropriate; negative tests. |
| Public exposure of uploaded files | Private buckets; short-lived signed URLs; no public object ACLs. |
| Prompt injection in PDF or retrieved page | Treat source text as untrusted data; isolate from system instructions; no tool privileges from document content. |
| Malicious or malformed PDF | File type and size checks, malware scanning, sandboxed parsing, page limits and timeouts. |
| Secret leakage | Environment/secret manager; never commit .env; redact logs and traces. |
| Sensitive content in observability | Minimize payload capture; redact or disable document body tracing; restrict trace access and retention. |
| Session/authentication abuse | Established auth provider, secure cookies/session handling, CSRF protections as applicable, rate limiting. |
| Unauthorized export/download | Re-check ownership and permissions at download time. |
| Source poisoning / incorrect citation | Preserve source URL, retrieval time, checksum and source tier; independent verification. |
| Data loss | Backups, restore tests, retention policy and user-requested deletion process. |

## Release blockers
Do not accept real confidential client documents until authentication, tenant isolation, private storage, deletion/retention, logging redaction, transport encryption and backup/restore have been implemented and tested.
