# Increment 12 Release Notes

**Feature:** OpenAI execution adapter for the six specialist agents  
**Database migration:** None; reuses migration `0014_research_agent_runs`  
**Default execution mode:** Mock

### Included
- Lazy OpenAI SDK adapter.
- Six specialist-specific system prompt profiles.
- JSON response parsing and validation.
- Evidence-ID allow-list validation.
- Token usage capture and run-level aggregation.
- Explicit `OPENAI_ENABLED` feature gate.
- Configurable model, output token ceiling and timeout.
- API request field `execution_mode` (`mock` or `openai`).
- Provider tests with mocked OpenAI responses.

### Not included
- Automatic legal citation certification.
- Current-law verification or web research by the model.
- Final legal opinion certification.
- Live OpenAI call validation in this release test suite.
