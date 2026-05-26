# External provider integration behind provider interface

Labels: `ready-for-agent`

## Parent

PRD: `docs/prd-rag-explanation.md`

## What to build

Add an external LLM provider implementation behind the same provider interface used by mock provider modes. The provider must be configured only through backend environment variables, enforce the v1 timeout policy, and fall back cleanly when the provider fails or returns unusable output.

This slice connects RAG Explanation to a real provider without letting provider-specific details leak into product logic or frontend code.

## Acceptance criteria

- [x] Provider selection is configurable by backend environment variable.
- [x] Mock provider modes remain available for local development and tests.
- [x] External provider API key and model configuration live only in backend environment variables.
- [x] No provider secrets are exposed to frontend code or committed files.
- [x] External provider calls use an 8-second provider timeout.
- [x] Provider timeout, provider error, and invalid provider output trigger Deterministic Fallback.
- [x] Product logic depends on a provider interface, not provider-specific implementation details.
- [x] Tests cover provider selection and failure handling without requiring a real provider call.
- [x] Documentation or env examples describe the new provider configuration without including real secrets.

## Blocked by

- Strict schema validation and Deterministic Fallback.
