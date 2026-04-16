# Tocky

Omnimodal ambient medical scribe that listens during clinical consultations, filters small talk, extracts medically relevant information in real-time, and generates SOAP notes for physician review.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, Alembic
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS v4
- **UI Library**: shadcn/ui (radix-mira style), Tiptap rich text editor
- **AI**: Qwen models via Alibaba Cloud DashScope API (per-workload model selection)
- **Pipeline**: LangGraph state graph for orchestrated multi-step processing
- **Auth**: better-auth (Next.js) + ES256 ECDSA JWT (FastAPI), RBAC (admin/doctor)
- **i18n**: next-intl with `.po` extraction, cookie-based locale (en, vi, ar, fr)
- **State**: Zustand (client), React Query (server)
- **Storage**: Alibaba Cloud OSS (audio) or local filesystem (dev)
- **Real-time**: WebSocket (live scribe), Server-Sent Events (batch processing)
- **Tooling**: pnpm, Turborepo, uv, Ruff, ESLint, Prettier

## Prerequisites

- Node.js >= 20 & [pnpm](https://pnpm.io/)
- Python 3.13 & [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL)

## Getting Started

```bash
# Install dependencies
pnpm install
cd apps/api && uv sync && cd ../..

# Copy environment variables
cp .env.example .env
# Edit .env — generate ES256 keys, fill in DashScope API key, OSS credentials

# Generate ES256 ECDSA keys for JWT auth
openssl ecparam -genkey -name prime256v1 -noout -out private.pem
openssl ec -in private.pem -pubout -out public.pem
# Paste the key contents into .env (TOCKY_JWT_PRIVATE_KEY, TOCKY_JWT_PUBLIC_KEY, NEXT_PUBLIC_JWT_PUBLIC_KEY)

# Start PostgreSQL
docker-compose up -d

# Run database migrations
cd apps/api && uv run alembic upgrade head && cd ../..

# Start all services (API on :8000, Web on :3000)
pnpm dev
```

### Sandbox Mode

For UI development without consuming API credits, set `TOCKY_SANDBOX_AI=true` in `.env`. This uses fake AI responses with configurable latency.

## Project Structure

```
apps/
  api/         FastAPI backend (Python)
    app/
      routers/       REST API (/api/v1/) + WebSocket (/ws/scribe/) + SSE
      services/      AI clients, audio processing, SOAP generation, auth
        graph/       LangGraph pipeline (state, nodes, orchestration)
      db_models/     SQLAlchemy ORM models
      models/        Pydantic request/response schemas
    prompts/         Language-specific AI prompt templates (Markdown)
    alembic/         Database migrations
  web/         Next.js frontend (TypeScript)
    app/
      (auth)/        Sign-in, sign-up pages
      (app)/         Doctor dashboard, consultations, scribe, SOAP review
      admin/         Admin dashboard, user management, quality metrics
    components/      Client components (sidebar, scribe UI, forms, Elfie integration)
    hooks/           Audio recorder, WebSocket, SSE, React Query hooks
    lib/             Auth, API client, Zustand stores
    i18n/            Cookie-based locale config
    messages/        .po translation files (auto-extracted)
packages/
  ui/          Shared shadcn/ui component library
  eslint-config/
  typescript-config/
```

## Common Commands

| Command | Description |
|---------|-------------|
| `pnpm dev` | Start all services |
| `pnpm build` | Build all packages |
| `pnpm lint` | Lint all packages |
| `pnpm format` | Format all packages |
| `pnpm typecheck` | Typecheck all packages |

### API (`apps/api`)

| Command | Description |
|---------|-------------|
| `uv run fastapi dev` | Start API dev server |
| `uv run ruff check app/` | Lint Python |
| `uv run ruff format app/` | Format Python |
| `uv run ty check app/` | Typecheck Python |
| `uv run alembic revision --autogenerate -m "msg"` | Create migration |
| `uv run alembic upgrade head` | Apply migrations |

### Adding UI Components

```bash
pnpm dlx shadcn@latest add <component> -c apps/web
```

Components are installed into `packages/ui/src/components/` and imported as:

```tsx
import { Button } from "@workspace/ui/components/button"
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `TOCKY_DATABASE_URL` | PostgreSQL connection string |
| `TOCKY_JWT_PRIVATE_KEY` | ES256 EC private key (PEM) for signing JWTs |
| `TOCKY_JWT_PUBLIC_KEY` | ES256 EC public key (PEM) for verifying JWTs |
| `TOCKY_DASHSCOPE_API_KEY` | Alibaba Cloud DashScope API key |
| `TOCKY_DASHSCOPE_BASE_URL` | DashScope REST API endpoint |
| `TOCKY_QWEN_MODEL_NAME` | Default model name (fallback for all workloads) |
| `TOCKY_QWEN_TRANSCRIPTION_MODEL` | Model for transcription (optional override) |
| `TOCKY_QWEN_CLASSIFICATION_MODEL` | Model for classification (optional override) |
| `TOCKY_QWEN_SOAP_MODEL` | Model for SOAP generation (optional override) |
| `TOCKY_QWEN_EXTRACTION_MODEL` | Model for entity extraction (optional override) |
| `TOCKY_DASHSCOPE_WS_BASE_URL` | DashScope WebSocket endpoint (streaming ASR) |
| `TOCKY_QWEN_STREAMING_ASR_MODEL` | Streaming ASR model name |
| `TOCKY_VAD_THRESHOLD` | Voice activity detection sensitivity (-1 to 1) |
| `TOCKY_VAD_SILENCE_DURATION_MS` | Silence duration before segment commit (200-6000ms) |
| `TOCKY_VAD_PREFIX_PADDING_MS` | Audio padding before detected speech onset |
| `TOCKY_SANDBOX_AI` | Enable sandbox mode (fake AI, no API cost) |
| `TOCKY_SANDBOX_AI_LATENCY` | Simulated AI response latency in sandbox mode |
| `TOCKY_OSS_ACCESS_KEY_ID` | Alibaba Cloud OSS access key |
| `TOCKY_OSS_ACCESS_KEY_SECRET` | Alibaba Cloud OSS secret key |
| `TOCKY_OSS_BUCKET_NAME` | OSS bucket for audio storage |
| `TOCKY_OSS_ENDPOINT` | OSS endpoint URL (omit for local file storage) |
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: http://localhost:8000) |
| `NEXT_PUBLIC_WS_URL` | Backend WebSocket URL (default: ws://localhost:8000) |
| `NEXT_PUBLIC_JWT_PUBLIC_KEY` | Public key for frontend JWT verification |

## Features

- **Ambient Scribe**: Real-time audio capture via browser microphone, streamed over WebSocket to backend with live transcript and SOAP updates
- **Batch Processing**: Upload audio files for async processing with SSE progress streaming
- **LangGraph Pipeline**: Multi-step AI processing (language detection, metadata extraction, transcript polishing, entity extraction, SOAP generation, QA review, ICD-10 suggestion)
- **Multilingual**: Vietnamese, Arabic (Egyptian + Gulf dialects), English, French with language-specific prompt templates
- **SOAP Notes**: Auto-generated Subjective/Objective/Assessment/Plan with version history and regeneration
- **QA Review Flags**: AI-generated review flags with confidence scoring; doctors can accept or dismiss flags
- **Medical NER**: Extracts symptoms, diagnoses, medications, procedures, vitals, allergies
- **ICD-10 Codes**: Auto-suggested diagnostic codes from medical entities with search
- **RBAC**: Admin dashboard (user management, quality metrics, prompt management) and doctor dashboard (consultations, scribe)
- **Quality Metrics**: Compare AI-generated vs finalized SOAP notes, edit distance analysis, flag acceptance rates, training data export
- **Elfie Integration**: Patient data fetching and care plan push (mock client for dev)
- **SOAP Versioning**: Immutable version history tracking source (AI-generated, doctor-edited, regenerated)
- **Prompt Management**: Admin UI for versioned prompt templates per language and workload
- **Audio Playback**: In-app audio player with stitched audio from segments
- **Keyboard Shortcuts**: Global hotkeys for recording controls and UI navigation
- **i18n**: Cookie-based locale switching with `.po` file extraction for translations
- **Sandbox Mode**: Fake AI responses for UI development without API cost
