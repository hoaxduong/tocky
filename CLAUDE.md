# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tocky is an omnimodal ambient medical scribe. It listens during clinical consultations, filters small talk, extracts medically relevant information in real-time, and generates SOAP notes (Subjective, Objective, Assessment, Plan) for physician review.

Fullstack monorepo: FastAPI (Python) backend, Next.js (React) frontend, and a shared shadcn/ui component library. Managed with pnpm workspaces and Turborepo.

## Commands

### Root (runs across all workspaces via Turbo)

- `pnpm dev` — start all services (API on :8000, Web on :3000)
- `pnpm build` — build all packages
- `pnpm lint` — lint all packages
- `pnpm format` — format all packages
- `pnpm typecheck` — typecheck all packages

### API (`apps/api`)

- `uv run fastapi dev` — start FastAPI dev server
- `uv run ruff check app/` — lint Python
- `uv run ruff format app/` — format Python
- `uv run ty check app/` — typecheck Python
- `uv sync` — install Python dependencies
- `uv run alembic revision --autogenerate -m "description"` — create migration
- `uv run alembic upgrade head` — apply migrations

### Web (`apps/web`)

- `pnpm --filter web dev` — start Next.js dev server
- `pnpm --filter web build` — build Next.js
- `pnpm --filter web lint` — lint frontend
- `pnpm --filter web typecheck` — typecheck frontend

### Infrastructure

- `docker-compose up` — start PostgreSQL (port 5432, user/pass/db: tocky/tocky/tocky)

### Adding shadcn/ui components

```bash
pnpm dlx shadcn@latest add <component> -c apps/web
```

Components land in `packages/ui/src/components/`. Import as `@workspace/ui/components/<name>`.

## Architecture

```
apps/
  api/          Python 3.13 FastAPI backend
    app/
      routers/       REST API + WebSocket + SSE
      services/      AI clients, audio processing, SOAP generation, LangGraph pipeline
        graph/       LangGraph state graph (nodes, pipeline, state)
      db_models/     SQLAlchemy ORM models
      models/        Pydantic request/response schemas
    prompts/         Language-specific prompt templates (Markdown)
    alembic/         Database migrations
  web/          Next.js 16 (App Router) frontend
packages/
  ui/           Shared shadcn/ui component library (Tailwind CSS v4, radix-mira style)
  eslint-config/
  typescript-config/
```

### API (`apps/api`)

- **Entry point**: `app/main.py` — FastAPI app with async lifespan (init DB, DashScope/sandbox client, streaming STT, prompt registry, event queue, Elfie client, storage)
- **Config**: `app/config.py` — Pydantic settings, env vars prefixed `TOCKY_`
- **Database**: `app/database.py` — SQLAlchemy async engine + asyncpg, PostgreSQL (no foreign keys — referential integrity handled in app logic)
- **Dependencies**: `app/dependencies.py` — FastAPI `Depends()` injection (DB sessions, auth deps)
- **ORM models**: `app/db_models/` — User, Session, Consultation, AudioSegment, Transcript, SOAPNote, SOAPNoteVersion, ICD10Code, FlagFeedback, PromptTemplate
- **Pydantic schemas**: `app/models/` — request/response models, WebSocket message protocol, review flags, quality metrics, prompt templates, Elfie DTOs
- **Routers**: `app/routers/` — REST endpoints under `/api/v1/`, WebSocket at `/ws/scribe/{id}`, SSE at `/api/v1/.../events`
- **Services**: `app/services/` — AI clients, audio processing, SOAP generation/review/versioning, LangGraph pipeline, ICD-10 suggestion, auth, storage, event queue, prompt registry
- **Prompts**: `prompts/` — 23 Markdown prompt templates (SOAP generation, extraction, transcript polishing, classification, entity extraction, ICD-10 suggestion) per language (en, vi, ar, fr)
- **Migrations**: `alembic/` — async Alembic runner (12 migration versions)

#### REST API (`/api/v1/`)

**Auth** (`/auth`):
- `POST /sign-up` — user registration
- `POST /sign-in` — login (returns cookies)
- `POST /sign-out` — logout (revokes refresh token)
- `POST /refresh` — refresh access token
- `GET /session` — current user session

**Consultations** (`/consultations`):
- `GET/POST /` — list (paginated, filterable by status) / create consultation
- `GET/PATCH /{id}` — get / update consultation
- `POST /{id}/archive` — archive consultation
- `DELETE /{id}` — delete archived consultation
- `POST /{id}/upload-audio` — upload audio file for batch processing
- `POST /{id}/retry-processing` — retry failed processing
- `GET /{id}/audio` — get audio URL and duration

**SOAP Notes** (`/consultations/{id}/soap-note`):
- `GET /` — get current SOAP note
- `PUT /` — update SOAP note sections
- `GET /versions` — list version history
- `POST /review` — run QA reviewer (generate review flags)
- `POST /finalize` — finalize (freeze) SOAP note
- `POST /regenerate` — regenerate SOAP note from transcript
- `POST /suggest-icd10` — suggest ICD-10 codes from medical entities
- `GET /flags/feedback` — list flag feedback
- `POST /flags/{flag_index}/feedback` — submit feedback on a review flag
- `GET /audio` — get stitched audio URL

**Transcripts** (`/consultations/{id}/transcripts`):
- `GET /` — transcript segments (optional `medically_relevant_only` filter)

**Events** (`/consultations/{id}/events`):
- `GET /` — SSE stream for batch processing progress (transcript, classification, progress, status events)

**ICD-10** (`/icd10`):
- `GET /search` — search ICD-10 codes by query

**Elfie** (`/elfie`):
- `GET /patient/{patient_identifier}` — fetch patient data
- `POST /push-care-plan` — push care plan to Elfie

**Admin** (`/admin`, admin role required):
- `GET /consultations` — all consultations
- `GET /stats` — system statistics
- `GET /quality-metrics` — AI vs finalized SOAP comparison
- `GET /flag-stats` — review flag acceptance/dismissal rates
- `GET /export-training-data` — JSONL training pairs stream
- `GET/POST /users` — list / create users
- `PATCH /users/{id}/role` — update role
- `POST /users/{id}/ban` — ban user
- `POST /users/{id}/unban` — unban user
- `DELETE /users/{id}` — delete user
- `GET/PUT /prompts/{slug}` — get / update prompt template
- `GET /prompts/{slug}/versions` — prompt version history
- `POST /prompts/{slug}/activate/{version}` — activate prompt version
- `GET /prompts` — list prompt templates

**Health** (unversioned):
- `GET /health` — health check

#### WebSocket (`/ws/scribe/{consultation_id}`)

Real-time audio streaming protocol. Auth via `?token={jwt}` query param or `tocky_access` cookie.

Client sends: `audio_chunk` (base64 audio), `start`, `stop`
Server sends: `transcript`, `soap_update`, `metadata_update`, `status`, `error`

#### LangGraph Pipeline (`app/services/graph/`)

Orchestrates batch audio processing through a state graph:

- `state.py` — `ScribePipelineState` TypedDict (inputs, intermediate results, errors)
- `nodes.py` — 7 async nodes: detect_language, extract_metadata, polish_transcript, extract_entities, generate_soap, review_soap, suggest_icd10
- `pipeline.py` — Compiled state graph with conditional routing:
  - `detect` → `meta` → `polish` → [periodic: SOAP → END | full: entities → SOAP → review → ICD-10 → END]

#### Auth & RBAC

- ES256 ECDSA JWT (private key signs on API, public key verifies on both sides)
- Cookie-based tokens: `tocky_access` (short-lived), `tocky_refresh` (7-day, DB-tracked)
- Roles: `admin`, `doctor` (default)
- Dependencies: `CurrentUserDep`, `AdminUserDep`, `DoctorUserDep`

### Web (`apps/web`)

- **App Router**: `app/` — server components by default, client components extracted to `components/`
- **Auth**: better-auth with JWT + admin plugin (`lib/auth.ts`, `lib/auth-client.ts`)
- **i18n**: next-intl with cookie-based locale detection and `.po` file extraction (`useExtracted` / `getExtracted`)
- **Providers**: `components/query-provider.tsx` (React Query, 60s staleTime), `components/theme-provider.tsx` (dark mode, 'd' hotkey), `components/hotkeys-provider.tsx` (global keyboard shortcuts)
- **State**: Zustand stores in `lib/stores/` (scribe session state, app-wide state)
- **Hooks**: `hooks/` — audio recorder, WebSocket scribe, SSE processing events, consultation/SOAP React Query hooks, SOAP versions, audio hotkeys, Elfie, admin quality, users
- **API client**: `lib/api.ts` — typed fetch wrapper with JWT auto-refresh on 401

#### Page structure (no locale prefix in URLs)

```
app/
  (auth)/sign-in, sign-up           — authentication pages
  (app)/dashboard                    — doctor dashboard
  (app)/consultations/               — list, new, [id] (scribe), [id]/soap (review)
  admin/                             — admin dashboard
  admin/users/                       — user management
  admin/consultations/               — all consultations (admin view)
  admin/quality/                     — quality metrics dashboard
  api/auth/[...all]/                 — better-auth API routes
```

#### Server/client component pattern

Pages are server components. Interactive logic lives in focused client components:
- `components/app-sidebar.tsx` — navigation, session, locale switcher
- `components/dashboard-content.tsx` — consultation stats + list
- `components/consultations-list.tsx` — filterable consultation grid
- `components/consultation-card.tsx` — consultation display card
- `components/new-consultation-dialog.tsx` — create consultation dialog
- `components/soap-review-form.tsx` — SOAP note editor with flag feedback
- `components/soap-section-editor.tsx` — individual S/O/A/P section editor
- `components/sign-in-form.tsx`, `sign-up-form.tsx` — auth forms
- `components/scribe/` — scribe-layout, recording-controls, audio-visualizer, transcript-panel, transcript-segment, soap-editor, consultation-header, language-selector
- `components/elfie/` — elfie-patient-card, elfie-push-dialog, elfie-vitals-tab, elfie-medications-tab, elfie-lifestyle-tab
- `components/admin-quality-dashboard.tsx` — quality metrics + flag stats
- `components/admin-users-table.tsx` — user management table
- `components/icd10-code-card.tsx` — ICD-10 code display
- `components/markdown-preview.tsx` — render Markdown SOAP notes
- `components/audio-player.tsx` — audio playback
- `components/upload-processing-view.tsx` — SSE progress for batch processing
- `components/locale-switcher.tsx` — cookie-based locale switching
- `components/hotkeys-provider.tsx` — global hotkey registry
- `components/status-badge.tsx`, `empty-state.tsx`, `page-header.tsx`, `skeletons.tsx` — shared UI

### UI Package (`packages/ui`)

- **Components**: `src/components/` — shadcn/ui (Button, Input, Form, Card, Badge, Tabs, DataTable, Dialog, etc.)
- **Styles**: `src/styles/globals.css` — Tailwind v4 theme with CSS variables
- **Utilities**: `src/lib/utils.ts` — `cn()` helper (clsx + tailwind-merge)

## Key Conventions

- **Python**: ruff for lint+format, target Python 3.13, line length 88
- **TypeScript/JS**: Prettier (no semicolons, double quotes, trailing commas), ESLint
- **Tailwind**: v4 with `@tailwindcss/postcss`; use `cn()` and `cva()` for class merging
- **i18n**: use `useExtracted()` (client) / `getExtracted()` (server) with English text as message IDs; `.po` files auto-extracted during build
- **Database**: no foreign keys or DB-level constraints; referential integrity in app logic
- **Auth**: ES256 ECDSA JWT shared between Next.js (better-auth) and FastAPI (pyjwt); cookie-based tokens
- **Environment**: copy `.env.example` to `.env`; all backend vars prefixed `TOCKY_`
- **Sandbox mode**: set `TOCKY_SANDBOX_AI=true` for fake AI responses with zero API cost (useful for UI development)
- **Prompts**: language-specific Markdown templates in `apps/api/prompts/`; managed via prompt registry with versioning in admin UI
