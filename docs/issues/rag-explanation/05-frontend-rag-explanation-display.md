# Frontend display for RAG Explanation

Labels: `ready-for-agent`

## Parent

PRD: `docs/prd-rag-explanation.md`

## What to build

Update the frontend recommendation flow to display RAG Explanation output as an enhancement over existing Recommendations. After a user requests Recommendations, the UI should request the RAG Explanation, show a concise summary and top-3 item explanations, and degrade gracefully when the response is a Deterministic Fallback.

This slice makes the feature visible to users while preserving the current Recommendation List and deterministic explanation behavior.

## Acceptance criteria

- [ ] The UI calls the RAG Explanation Endpoint after Recommendation generation without changing ranking behavior.
- [ ] The UI displays the Structured Explanation summary.
- [ ] The UI displays item-level explanations for the top 3 Recommendations in Recommendation List order.
- [ ] If fewer than 3 Recommendations exist, the UI handles the shorter item explanation list.
- [ ] The UI handles `explanation_source: \"deterministic_fallback\"` with restrained fallback copy instead of an error wall.
- [ ] The UI does not expose provider name, provider model, provider API key, or raw prompt details.
- [ ] The UI remains usable if the RAG request fails or times out.
- [ ] Frontend tests or manual verification cover success, fallback, and unavailable states.

## Blocked by

- Backend tracer: mock RAG Explanation endpoint.
- Strict schema validation and Deterministic Fallback.
