# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tocky is a fullstack monorepo: FastAPI (Python) backend, Next.js (React) frontend, and a shared shadcn/ui component library. Managed with pnpm workspaces and Turborepo.

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

- **Entry point**: `app/main.py` — FastAPI app with async lifespan (init/close DB)
- **Config**: `app/config.py` — Pydantic settings, env vars prefixed `TOCKY_`
- **Database**: `app/database.py` — SQLAlchemy async engine + asyncpg, PostgreSQL
- **Dependencies**: `app/dependencies.py` — FastAPI `Depends()` injection (DB sessions)
- **ORM models**: `app/db_models/`
- **Pydantic schemas**: `app/models/`
- **Routers**: `app/routers/` — endpoint modules, mounted in main.py
- **Migrations**: `alembic/` — async Alembic runner

### Web (`apps/web`)

- **App Router**: `app/` — layouts, pages, server/client components
- **Providers**: `components/query-provider.tsx` (React Query, 60s staleTime), `components/theme-provider.tsx` (dark mode, 'd' hotkey)
- **State**: Zustand stores in `lib/stores/`
- **Hooks**: `hooks/`

### UI Package (`packages/ui`)

- **Components**: `src/components/` — shadcn/ui (Button, Input, Form, DataTable, etc.)
- **Styles**: `src/styles/globals.css` — Tailwind v4 theme with CSS variables
- **Utilities**: `src/lib/utils.ts` — `cn()` helper (clsx + tailwind-merge)

## Key Conventions

- **Python**: ruff for lint+format, target Python 3.13, line length 88
- **TypeScript/JS**: Prettier (no semicolons, double quotes, trailing commas), ESLint
- **Tailwind**: v4 with `@tailwindcss/postcss`; use `cn()` and `cva()` for class merging
- **Environment**: copy `.env.example` to `.env`; database URL is `TOCKY_DATABASE_URL`
