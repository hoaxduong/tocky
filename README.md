# Tocky

Omnimodal ambient medical scribe that listens during clinical consultations, filters small talk, extracts medically relevant information in real-time, and generates SOAP notes for physician review.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, Alembic
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS v4
- **UI Library**: shadcn/ui (radix-mira style)
- **AI**: Qwen2.5-Omni via Alibaba Cloud DashScope API
- **Auth**: better-auth (Next.js) + JWT validation (FastAPI), RBAC (admin/doctor)
- **i18n**: next-intl with `.po` extraction, cookie-based locale (en, vi, ar)
- **State**: Zustand (client), React Query (server)
- **Storage**: Alibaba Cloud OSS (audio)
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
# Edit .env to fill in DashScope API key, OSS credentials, AUTH_SECRET

# Start PostgreSQL
docker-compose up -d

# Run database migrations
cd apps/api && uv run alembic upgrade head && cd ../..

# Start all services (API on :8000, Web on :3000)
pnpm dev
```

## Project Structure

```
apps/
  api/         FastAPI backend (Python)
    app/
      routers/       REST API (/api/v1/) + WebSocket (/ws/scribe/)
      services/      DashScope client, OSS client, audio processor, SOAP generator, auth
      db_models/     SQLAlchemy ORM (Consultation, AudioSegment, Transcript, SOAPNote)
      models/        Pydantic request/response schemas
    alembic/         Database migrations
  web/         Next.js frontend (TypeScript)
    app/
      (auth)/        Sign-in, sign-up pages
      (app)/         Doctor dashboard, consultations, scribe
      admin/         Admin dashboard, user management
    components/      Client components (sidebar, forms, scribe UI)
    hooks/           Audio recorder, WebSocket, React Query hooks
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
| `TOCKY_AUTH_SECRET` | Shared JWT secret (must match between Next.js and FastAPI) |
| `TOCKY_DASHSCOPE_API_KEY` | Alibaba Cloud DashScope API key for Qwen2.5-Omni |
| `TOCKY_DASHSCOPE_BASE_URL` | DashScope API endpoint |
| `TOCKY_QWEN_MODEL_NAME` | Model name (default: qwen2.5-omni-7b) |
| `TOCKY_OSS_ACCESS_KEY_ID` | Alibaba Cloud OSS access key |
| `TOCKY_OSS_ACCESS_KEY_SECRET` | Alibaba Cloud OSS secret key |
| `TOCKY_OSS_BUCKET_NAME` | OSS bucket for audio storage |
| `TOCKY_OSS_ENDPOINT` | OSS endpoint URL |
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: http://localhost:8000) |
| `NEXT_PUBLIC_WS_URL` | Backend WebSocket URL (default: ws://localhost:8000) |

## Features

- **Ambient Scribe**: Real-time audio capture via browser microphone, streamed over WebSocket to backend
- **Multilingual**: Vietnamese (VietMed medical entities), Arabic dialects (Egyptian, Gulf), English
- **SOAP Notes**: Auto-generated Subjective/Objective/Assessment/Plan from consultation transcript
- **Small Talk Filtering**: AI classifies each transcript segment as medically relevant or small talk
- **Medical NER**: Extracts symptoms, diagnoses, medications, procedures, vitals, allergies
- **RBAC**: Admin dashboard (user management, system stats) and doctor dashboard (consultations, scribe)
- **i18n**: Cookie-based locale switching with `.po` file extraction for translations
