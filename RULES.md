# Project Rules

## Fixed Tech Stack

- Backend: FastAPI + ONNX Runtime + Redis
- Training: PyTorch Lightning (AMP + grad accumulation)
- Frontend: React + TypeScript + D3
- Infra: Docker
- Deployment: AWS EC2

## Change Principles

- Work on one feature at a time.
- Bug fixes must be minimal changes.
- No large-scale refactors.
- After each checkpoint, remind me to git commit.

## Security

- Do not commit `.env` files.
- Never log secrets or sensitive data.

## Runtime Requirements

- Every service must expose `/healthz`.
- API responses must include a `model_version` field (define in code later).
