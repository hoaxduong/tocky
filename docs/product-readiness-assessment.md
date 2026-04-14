# Tocky — Product-Readiness Assessment

> Generated: 2026-04-14

---

## Current Strengths

- **Clean monorepo** — Turbo + pnpm workspace well-configured
- **Good API design** — Versioned REST endpoints, proper async patterns, SQLAlchemy ORM
- **Auth architecture** — ES256 JWT, middleware-level route protection, RBAC (admin/doctor)
- **i18n** — 4 locales (en/vi/ar/fr) with PO files, RTL support
- **Real-time pipeline** — WebSocket audio streaming + SSE for upload processing
- **State management** — Clean separation: Zustand for UI, React Query for server data

---

## Critical Gaps (Must Fix Before Production)

### 1. Zero Test Coverage

No tests exist anywhere — backend or frontend. This is the single biggest risk.

**Recommended:**
- **Backend**: pytest + httpx for API integration tests, WebSocket connection tests
- **Frontend**: Vitest for hooks/utils, Playwright for E2E (auth flow, recording flow, SOAP review)
- Start with the highest-value paths: auth, consultation CRUD, WebSocket scribe session

### 2. No CI/CD Pipeline

No GitHub Actions, no automated builds, no deployment strategy.

**Recommended:**
- GitHub Actions: lint + typecheck + test on PR, build + deploy on merge to main
- Production Dockerfiles for both API and web (multi-stage builds)
- Deployment target: consider Railway, Fly.io, or AWS ECS for simplicity

### 3. Security Hardening

| Issue | Where | Fix |
|-------|-------|-----|
| `COOKIE_SECURE = False` hardcoded | `apps/api/app/routers/auth.py` | Move to env variable, `True` in production |
| CORS origin hardcoded to localhost | `apps/api/app/main.py` | Use `TOCKY_CORS_ORIGINS` env var |
| No rate limiting | Entire API | Add `slowapi` on auth + upload endpoints |
| JWT token in WebSocket query param | `scribe_ws.py` | Logged in access logs — use cookie-based auth |
| No security headers | API + Web | Add HSTS, X-Content-Type-Options, X-Frame-Options |
| No password complexity rules | Sign-up flow | Enforce min 8 chars + complexity on both client and server |
| No CSRF protection | Auth cookies | Add CSRF tokens for state-changing operations |

### 4. No Error Boundaries / Error Pages

- No `error.tsx` at any route level — unhandled exceptions crash silently
- No custom 404 or 500 pages
- No global exception handler in FastAPI

**Recommended:**
- Add `app/error.tsx` and `app/not-found.tsx` in Next.js
- Add global `@app.exception_handler(Exception)` in FastAPI that returns sanitized errors

### 5. No Monitoring / Observability

- No error tracking (Sentry), no APM, no structured logging
- Health endpoint returns static "ok" — doesn't check DB or external services

**Recommended:**
- **Sentry** for both Python and Next.js (quick setup, free tier)
- Structured JSON logging with request IDs for tracing
- Health check that verifies DB connectivity + DashScope availability

---

## Important Improvements (Product Quality)

### 6. WebSocket Robustness

- No heartbeat/keepalive — stale connections go undetected
- No reconnection logic — dropped connections require full page refresh
- No message schema validation — malformed JSON causes crashes
- `ScriptProcessor` is deprecated — migrate to `AudioWorklet`

### 7. Database Production Readiness

- Connection pool not tuned (using defaults: 5 connections, 10 overflow)
- No backup strategy — data loss risk
- Missing indexes on `consultations.status`, `sessions.expires_at`
- No seed data for development/testing

### 8. Accessibility

- No ARIA labels on interactive elements
- No `aria-live` regions for real-time updates (transcripts, recording status)
- No skip-to-content links
- No focus management on dialogs
- Medical software often needs WCAG AA compliance — this is far from it

### 9. Form Validation

- Auth forms use minimal browser validation only
- No field-level error messages
- Consider Zod + React Hook Form (already in dependencies but underutilized)

---

## Features to Add for Product-Readiness

### 10. Multi-Tenancy / Organization Model

Currently single-tenant. For a real product, you'd need:
- Organizations/clinics with their own doctors
- Invitation flow for adding doctors to an organization
- Per-organization settings and billing

### 11. Audit Trail

Medical software needs compliance:
- Log every SOAP note view, edit, and finalize action
- Track who accessed which patient data and when
- Immutable audit log (append-only table)

### 12. Data Export & Interoperability

- Export SOAP notes as PDF
- HL7 FHIR integration for EHR systems
- CSV/Excel export for consultation history

### 13. Patient Consent Management

- Record patient consent for audio recording
- Consent withdrawal flow with data deletion
- Consent audit trail

### 14. Offline / Degraded Mode

- Service worker for basic offline functionality
- Local audio buffering when network drops during recording
- Queue and retry for failed uploads

### 15. User Onboarding

- First-run setup wizard
- Sample/demo consultation
- Guided tour of the scribe interface

### 16. Notification System

- Email notifications for completed SOAP notes
- In-app notifications for processing status
- WebSocket-based real-time notification channel

### 17. Analytics Dashboard

- Consultation volume trends
- Average recording duration
- SOAP note completion rates
- AI suggestion acceptance rates

---

## Detailed Audit by Area

### Backend (FastAPI)

| Category | Status | Key Findings |
|----------|--------|--------------|
| **Error Handling** | Partial | Generic exception catching, no global handler, error detail leaking |
| **Validation** | Partial | No password rules, missing language enum, JSON schema not validated |
| **Security** | Issues | Hardcoded CORS, COOKIE_SECURE=False, no rate limiting, token in URL param |
| **Testing** | None | Zero test coverage |
| **Logging** | Basic | Text-only, no structured logging, no correlation IDs |
| **Database** | Good | Proper migrations, indexed appropriately, safe ORM queries |
| **API Design** | Good | Versioned, paginated, consistent response models |
| **WebSocket** | Issues | No heartbeat, token in query param, no schema validation, race conditions |
| **Configuration** | Issues | Hardcoded values, secrets in env, no pool tuning |
| **Performance** | Good | Async throughout, background tasks properly managed, but no caching |

#### Backend Details

**Error Handling:**
- No global exception handler middleware configured
- `apps/api/app/routers/scribe_ws.py:252-256` — Bare `Exception` catch with generic error
- `apps/api/app/services/auth.py:78-81` — `jwt.InvalidTokenError` leaks token validation details
- `apps/api/app/routers/consultations.py:196-217` — Error message truncated but stored raw

**Validation:**
- `apps/api/app/models/user.py:43` — `password: str` with no minimum length or complexity checks
- `apps/api/app/models/consultation.py:10` — `language` not validated against enum
- `apps/api/app/routers/scribe_ws.py:101` — JSON parsed without schema validation

**Security:**
- `apps/api/app/main.py:122-129` — CORS hardcoded to `http://localhost:3000`
- `apps/api/app/routers/auth.py:28-29` — `COOKIE_SECURE = False` hardcoded
- `apps/api/app/routers/scribe_ws.py:28` — Token via query parameter (logged in access logs)
- No rate limiting middleware anywhere
- No security headers (HSTS, X-Content-Type-Options, X-Frame-Options)

**Database:**
- `apps/api/app/database.py:20` — Default pool settings (pool_size=5, max_overflow=10)
- Missing indexes: `consultations.status`, `sessions.expires_at`
- No backup strategy documented
- 10 Alembic migrations, well-structured

**WebSocket:**
- No ping/pong heartbeat mechanism
- No maximum message size configured (`max_size=None` in `streaming_stt.py:89`)
- No reconnection/session resumption support
- Race conditions between concurrent WebSocket connections for same consultation

### Frontend (Next.js)

| Area | Status | Key Strengths | Critical Gaps |
|------|--------|---------------|---------------|
| Error Handling | Partial | API-level 401 retry, form errors | No error boundaries, no 404/500 pages |
| State Management | Strong | Zustand + React Query separation, proper invalidation | No optimistic updates, no persistence |
| Auth Flow | Strong | JWT middleware, role-based routing, token refresh | No proactive expiration, CSRF unaddressed |
| Accessibility | Weak | Keyboard shortcuts, form labels | No ARIA, no screen reader support, no focus mgmt |
| Performance | Good | App Router, SSR layouts, proper caching | No code-splitting, large components, no service worker |
| SEO | Minimal | Basic metadata, RTL support | No OG tags, no robots.txt/sitemap |
| Testing | None | — | Zero test coverage |
| i18n | Complete | 4 locales, PO format, RTL support | No locale-aware formatting, no pluralization |
| Responsive | Good | Mobile-first Tailwind, collapsible sidebar | No touch optimization, no orientation detection |
| Real-time | Strong | WebSocket + SSE, audio buffering, error states | ScriptProcessor deprecated, no reconnection logic |
| Forms | Basic | Controlled components, file validation | No field validation library, no async validation |
| Routing | Strong | Middleware protection, dynamic routes, breadcrumbs | No error pages, no prefetching |

#### Frontend Details

**Error Handling:**
- No `error.tsx` files at app root or any segment level
- No custom 404 or 500 pages
- `apps/web/lib/api.ts` — Custom `ApiError` class with 401 refresh retry (good)
- No global error logging/analytics integration

**Auth Flow:**
- `apps/web/middleware.ts` — ES256 JWT verification, role-based routing
- `apps/web/lib/api.ts` — Automatic token refresh with deduplication on 401
- `apps/web/lib/auth.ts` — Sign-in/sign-up/sign-out/refresh/session functions
- Gap: No session polling for proactive token expiration detection
- Gap: `callbackUrl` param not actually used after sign-in (always redirects to `/dashboard`)

**Accessibility:**
- No ARIA labels on interactive elements
- No `aria-live` regions for live updates (SSE segments, WebSocket messages)
- No skip-to-content links
- No `prefers-reduced-motion` support
- Audio visualizer has keyboard shortcuts (`apps/web/hooks/use-audio-hotkeys.ts`) — good

**Real-time:**
- `apps/web/hooks/use-scribe-websocket.ts` — WebSocket for live scribe
- `apps/web/hooks/use-audio-recorder.ts` — MediaStream + ScriptProcessor (deprecated)
- `apps/web/hooks/use-processing-events.ts` — SSE with `fetchEventSource`
- No WebSocket reconnection logic
- Audio chunks: 4096 samples at 16kHz = ~256ms per chunk

### Infrastructure & DevOps

| Category | Status | Notes |
|----------|--------|-------|
| **CI/CD** | Missing | No GitHub Actions, no automated testing/deployment |
| **Docker** | Partial | Only dev Postgres; no production images |
| **Environments** | Risky | `.env.example` good, but needs secrets manager for production |
| **Monorepo** | Excellent | Turbo + pnpm well-configured |
| **Dependencies** | Good | Modern stacks; no audit automation |
| **Documentation** | Minimal | README present; missing deployment guides |
| **Linting** | Good | ESLint + Prettier + Ruff; no pre-commit hooks |
| **Security** | Weak | CORS hardcoded, no security headers, no secrets manager |
| **Database** | Good | Alembic migrations; no backup strategy |
| **Monitoring** | Missing | No APM, no error tracking, no structured logging |

---

## Suggested Roadmap

| Phase | Focus | Effort |
|-------|-------|--------|
| **Phase 1** | Security hardening + error handling + CI/CD | 1-2 weeks |
| **Phase 2** | Test suite (critical paths) + monitoring (Sentry) | 1-2 weeks |
| **Phase 3** | WebSocket robustness + AudioWorklet migration | 1 week |
| **Phase 4** | Accessibility (WCAG AA) + form validation | 1 week |
| **Phase 5** | Audit trail + patient consent + PDF export | 2 weeks |
| **Phase 6** | Multi-tenancy + onboarding + analytics | 2-3 weeks |
