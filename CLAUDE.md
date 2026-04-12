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
  web/          Next.js 16 (App Router) frontend
packages/
  ui/           Shared shadcn/ui component library (Tailwind CSS v4, radix-mira style)
  eslint-config/
  typescript-config/
```

### API (`apps/api`)

- **Entry point**: `app/main.py` — FastAPI app with async lifespan (init DB, DashScope client)
- **Config**: `app/config.py` — Pydantic settings, env vars prefixed `TOCKY_`
- **Database**: `app/database.py` — SQLAlchemy async engine + asyncpg, PostgreSQL (no foreign keys — referential integrity handled in app logic)
- **Dependencies**: `app/dependencies.py` — FastAPI `Depends()` injection (DB sessions, auth deps)
- **ORM models**: `app/db_models/` — Consultation, AudioSegment, Transcript, SOAPNote
- **Pydantic schemas**: `app/models/` — request/response models + WebSocket message protocol
- **Routers**: `app/routers/` — REST endpoints under `/api/v1/`, WebSocket at `/ws/scribe/{id}`
- **Services**: `app/services/` — auth (JWT), DashScope client, OSS client, audio processor, SOAP generator
- **Migrations**: `alembic/` — async Alembic runner

#### REST API (`/api/v1/`)

- `GET/POST/PATCH/DELETE /consultations/` — consultation CRUD (requires auth)
- `GET/PUT /consultations/{id}/soap-note/` — SOAP note read/update
- `POST /consultations/{id}/soap-note/finalize` — finalize SOAP note
- `GET /consultations/{id}/transcripts/` — transcript segments
- `GET /admin/consultations` — all consultations (admin only)
- `GET /admin/stats` — system statistics (admin only)

#### WebSocket (`/ws/scribe/{consultation_id}?token={jwt}`)

Real-time audio streaming protocol: client sends audio chunks, server responds with transcript segments and SOAP updates.

#### Auth & RBAC

- JWT validation via shared `AUTH_SECRET` with better-auth (Next.js)
- Roles: `admin`, `doctor` (default)
- Dependencies: `CurrentUserDep`, `AdminUserDep`, `DoctorUserDep`

### Web (`apps/web`)

- **App Router**: `app/` — server components by default, client components extracted to `components/`
- **Auth**: better-auth with JWT + admin plugin (`lib/auth.ts`, `lib/auth-client.ts`)
- **i18n**: next-intl with cookie-based locale detection and `.po` file extraction (`useExtracted` / `getExtracted`)
- **Providers**: `components/query-provider.tsx` (React Query, 60s staleTime), `components/theme-provider.tsx` (dark mode, 'd' hotkey)
- **State**: Zustand stores in `lib/stores/` (scribe session state)
- **Hooks**: `hooks/` — audio recorder, WebSocket scribe, consultation/SOAP React Query hooks
- **API client**: `lib/api.ts` — typed fetch wrapper with JWT

#### Page structure (no locale prefix in URLs)

```
app/
  (auth)/sign-in, sign-up           — authentication pages
  (app)/dashboard                    — doctor dashboard
  (app)/consultations/               — list, new, [id] (scribe), [id]/soap (review)
  admin/                             — admin dashboard, users, consultations
  api/auth/[...all]/                 — better-auth API routes
```

#### Server/client component pattern

Pages are server components. Interactive logic lives in focused client components:
- `components/app-sidebar.tsx` — navigation, session, locale switcher
- `components/dashboard-content.tsx` — consultation stats + list
- `components/consultations-list.tsx` — filterable consultation grid
- `components/new-consultation-form.tsx` — create consultation form
- `components/soap-review-form.tsx` — SOAP note editor
- `components/sign-in-form.tsx`, `sign-up-form.tsx` — auth forms
- `components/scribe/` — recording controls, audio visualizer, transcript panel, SOAP editor
- `components/locale-switcher.tsx` — cookie-based locale switching

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
- **Auth**: JWT shared secret between Next.js (better-auth) and FastAPI (pyjwt)
- **Environment**: copy `.env.example` to `.env`; all backend vars prefixed `TOCKY_`
