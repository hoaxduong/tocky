# Tocky

Fullstack monorepo with a FastAPI backend, Next.js frontend, and shared UI component library.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, Alembic
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS v4
- **UI Library**: shadcn/ui (radix-mira style)
- **State**: Zustand (client), React Query (server)
- **Tooling**: pnpm, Turborepo, uv, Ruff, ESLint, Prettier

## Prerequisites

- Node.js & [pnpm](https://pnpm.io/)
- Python 3.13 & [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL)

## Getting Started

```bash
# Install dependencies
pnpm install
cd apps/api && uv sync && cd ../..

# Copy environment variables
cp .env.example .env

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
  api/       FastAPI backend (Python)
  web/       Next.js frontend (TypeScript)
packages/
  ui/        Shared shadcn/ui component library
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
