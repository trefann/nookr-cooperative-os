# Nookr

**AI-powered intelligence for cooperative workforce management.**

An operating system for labour cooperatives, built for Smart India Hackathon 2026 —
**SIH26089: Cooperative Gig Services Platform for Household & Community Services**.

Nookr is not a service marketplace. A marketplace connects a customer to a
worker and takes a cut. This product gives the cooperative the intelligence to
run its own workforce:

```
Customer need
      ↓
AI service understanding      (natural language → structured requirement)
      ↓
Skill / resource identification
      ↓
Demand & workforce analysis
      ↓
AI + geo matching
      ↓
Fair worker allocation        (workload-aware, and it explains itself)
      ↓
Service execution → Payment → Feedback
      ↓
Cooperative intelligence
      ↓
Demand forecasting → Workforce planning → Skill gaps → Welfare
```

> Nookr does not replace cooperative workers. It gives cooperatives the
> intelligence to organise, support and empower them.

---

## Contents

- [Quick start](#quick-start)
- [Demo accounts](#demo-accounts)
- [The five-minute demo](#the-five-minute-demo)
- [Architecture](#architecture)
- [Where the AI is, and what it actually is](#where-the-ai-is-and-what-it-actually-is)
- [Data model](#data-model)
- [API](#api)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Honest limitations](#honest-limitations)

---

## Quick start

Prerequisites: **Python 3.11+** and **Node 20+**. No database server, no Docker
and no API keys are required to run the demo.

### 1. Backend

```bash
cd backend
python -m venv .venv
```

Activate the environment — `.venv\Scripts\activate` on Windows, or
`source .venv/bin/activate` on macOS and Linux — then:

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Create the schema and load eight weeks of demo history:

```bash
alembic upgrade head
```

```bash
python -m app.db.seed --reset
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now on <http://127.0.0.1:8000>, with interactive docs at
<http://127.0.0.1:8000/docs> and a self-report at
<http://127.0.0.1:8000/api/health>.

### 2. Frontend

In a second terminal:

```bash
cd frontend
```

```bash
npm install
```

```bash
npm run dev
```

Open <http://127.0.0.1:5173>. In development the dev server proxies `/api` to
the backend, so no environment file is needed.

---

## Demo accounts

All three are seeded, clearly labelled in the interface, and reachable with one
click from the landing page — judges never have to register or type credentials.

| Role | Email | Password | What it shows |
| --- | --- | --- | --- |
| Customer | `customer@demo.com` | `demo1234` | Priya Sharma. Request a service, track it, pay, rate. |
| Worker | `worker@demo.com` | `demo1234` | Kumar Selvan, plumber. Accept, run and complete jobs; earnings and welfare. |
| Cooperative admin | `admin@demo.com` | `demo1234` | The intelligence dashboard, forecasting, planning, skill gaps. |

---

## The five-minute demo

Turn on **🎯 SIH Demo Mode** from the landing page. A control strip appears with
the ten scripted steps, one-click persona switching, and **Reset Demo**, which
restores the exact starting dataset so the whole flow can be run again.

| # | Step | Where | What to point at |
| --- | --- | --- | --- |
| 1 | Customer describes a need | `/customer` | *"My kitchen sink is leaking. I need a plumber tomorrow morning."* → Plumbing / Kitchen Sink Leakage / Plumbing + Pipe Repair / Normal / Tomorrow Morning, and the engine that produced it is named. |
| 2 | Eligible workers | `/matching` | 26 members considered, 8 eligible; the rest excluded with reasons ("No matching skill", "No verified certification for Solar Installation"). |
| 3 | Fair allocation | `/matching` | **Kumar Selvan scores 89%.** Rajesh Nair is closer (1.8 km) and better rated (4.8) but is at 83% of capacity and scores 67%. Fathima Beevi is nearest of all (1.0 km) and still loses. |
| 4–6 | Worker accepts, starts, completes | `/worker` | Availability flips to *On a job* while the work runs, and back afterwards. |
| 7 | Customer pays | `/bookings/:id` | ₹650 → worker ₹560, cooperative ₹40, welfare ₹20, technology ₹30. Invoice `SAH-####`, printable and downloadable. |
| 8 | Customer rates | `/bookings/:id` | The worker's average moves immediately, from real rows. |
| 9 | Dashboard updates | `/dashboard` | Total jobs, ratings and revenue all move by exactly this job. |
| 10 | AI recommends an action | `/forecast` | *"Electrical demand is forecast to run +13% against its four-week average. Available electrical workers: 4 — required: 6 — shortage: 2. Activate 2 additional electrical workers and prioritise Zone 3."* |

The scripted scenario is deterministic: the seed uses a fixed random seed, and
it deliberately keeps the demo worker's diary clear around the scripted slot so
the same worker wins every time. **The scoring model itself is untouched by
this** — only the seeded starting data.

---

## Architecture

```
React 19 + TypeScript + Vite + Tailwind v4 + Recharts
        │  REST over JSON, bearer JWT
        ▼
FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
        ▼
PostgreSQL   (SQLite by default for a zero-setup local demo)
```

```
backend/
  alembic/            migrations
  app/
    api/routes/       HTTP layer only: auth, workers, bookings, customer,
                      intelligence, transactions, demo, catalogue
    api/serializers   ORM → response models, in one place
    core/             config, security, deps, errors, timeutils
    db/               engine, session, seed data and seed script
    models/           SQLAlchemy models and the booking state machine
    schemas/          Pydantic request/response models
    services/         all business logic and every AI engine
  scripts/            developer utilities
  tests/              43 tests
frontend/
  src/
    components/ui/       design-system primitives
    components/charts/   Recharts wrappers, themed once
    components/domain/   booking cards, score breakdown, invoice, tracking
    components/layout/   app shell, sidebar, language, demo bar
    pages/               one file per route
    lib/                 API client, typed endpoints, formatting, speech
    i18n/                en · हिन्दी · தமிழ் · తెలుగు
```

Business rules live in `app/services/`, never in route handlers, so the HTTP
API, the seed script and the demo flow all move data through exactly the same
state machine.

### Routes

`/login` · `/register` · `/customer` · `/worker` · `/dashboard` · `/services` ·
`/bookings` · `/bookings/:id` · `/matching` · `/forecast` · `/workforce` ·
`/welfare` · `/analytics`

Navigation is filtered by role, so nobody is offered a screen they cannot open.

---

## Where the AI is, and what it actually is

This is stated plainly because a judge will ask. Nothing here is described as
deep learning, and the API reports which engine produced every answer.

### AI #1 — Service understanding · `POST /api/ai/understand-request`

Natural language → `{service, problem, skills, workers_required, urgency,
preferred_time}`.

Two engines, in this order:

1. **LLM** — used only when `AI_API_KEY` is configured. Whatever it returns is
   validated against the cooperative's own service and skill catalogue before
   it is trusted; scheduling stays with the deterministic parser so the slot is
   always a real datetime.
2. **Rule engine** — a keyword and pattern engine covering all seven services
   with ~40 problem patterns, urgency detection, plural-tolerant matching and
   relative-time parsing ("tomorrow morning", "today evening at 6 pm", "this
   weekend"). This is the guaranteed path and needs no network at all.

Any LLM failure degrades silently to the rule engine, and the `method` field
says so. When nothing is recognised, confidence drops below 0.5 and the UI asks
the customer to confirm the service rather than guessing.

### AI #2 — Explainable matching and fair allocation · `POST /api/matching`

A transparent weighted model over real database facts:

| Component | Weight | What it measures |
| --- | --- | --- |
| Skill match | 30% | Coverage of required skills, weighted by proficiency, plus primary-service fit |
| Availability | 20% | Status, the weekly working pattern, and clashes near the requested slot |
| Location | 15% | Haversine distance × a road factor, decaying to a 25 km service radius |
| Rating | 15% | Bayesian-shrunk towards the cooperative average, so one 5-star job is not decisive |
| **Fairness** | **20%** | **How much of the member's weekly capacity is already committed** |

Hard constraints applied before scoring: verified profile, not off duty, holds
at least one required skill, holds a **verified certification** where the skill
demands one (solar, refrigeration), and is not more than 25% over capacity.
Every exclusion is returned with its reason.

The full component breakdown, each with a human-readable justification, is
returned with every candidate and stored on the booking when a worker is
allocated — so "why this worker?" can always be answered after the fact.

Workload is *derived*, never stored: it is the count of jobs committed inside a
rolling seven-day window against the member's weekly capacity. The same
definition drives matching, the utilisation panel and the workforce planner, so
the three can never disagree.

### AI #3 — Demand forecasting · `GET /api/forecast`

A weighted moving average over four weeks (40/30/20/10, recent weeks first),
adjusted by a **halved** recent trend and capped, so a 60% spike does not become
a 60% forecast. Confidence falls with short history and with volatility, and is
reported per service.

Change is reported against the four-week weighted baseline — the number the
model actually reasons about — with change-versus-last-week given separately so
neither is misread.

### AI #4 — Workforce planning · `GET /api/workforce`

`required = ceil(forecast demand ÷ (average weekly capacity × 85% target
utilisation))`, compared against verified, on-duty members per service. The gap
becomes a concrete recommendation, including which zone to prioritise and which
surplus service could be cross-trained.

### AI #5 — Skill gap detection · `GET /api/workforce`

Recent per-skill demand, projected forward by each skill's growth factor, against
the members who can actually serve it. Two clearly-labelled regimes:

- **General skills** — every holder can serve them full time.
- **Specialist skills** (certified or emerging) — a holder can give roughly 30%
  of their month to one specialist skill, and certified skills count only
  members with a verified credential.

On the seeded data this surfaces *Solar Installation: required 6, available 4,
gap 2 → train and certify 2 eligible electrical workers*, entirely derived from
the booking history.

### What is **not** AI

The payment split, the booking state machine, pricing and the invoice are plain
deterministic business logic, and are labelled as such. Payments are
**simulated**; no real financial transaction occurs anywhere in this system.

### The workload projection is a simulation, and says so

The "fair workload distribution" chart is a **projection**, not measured
history, and is labelled that way on screen and in the API. The model is stated
in full: over the next seven days a fraction of current commitments completes
and leaves the rolling window, the same volume of new work arrives, and it is
shared out in proportion to remaining headroom. Total load is conserved; only
its distribution changes.

---

## Data model

18 tables: `cooperatives`, `zones`, `users`, `workers`, `worker_skills`,
`certifications`, `worker_availability`, `services`, `skills`, `service_skills`,
`bookings`, `booking_skills`, `payments`, `ratings`, `welfare`,
`demand_records`, `demand_forecasts`, `notifications`.

### The booking state machine

```
REQUESTED → ASSIGNED → ACCEPTED → IN_PROGRESS → COMPLETED → PAID → RATED
     ↓          ↓ ↘ DECLINED → ASSIGNED
 CANCELLED  CANCELLED
```

Enforced in the service layer. An illegal transition returns **409** with the
reason and the legal next steps, never a silent corruption.

### Seed data

`python -m app.db.seed --reset` builds a cooperative in Coimbatore with a fixed
random seed, so the dataset is byte-identical every run:

- 1 cooperative, **5 zones**, **7 service categories**, **35 skills**
- **26 workers** with skills, proficiencies, certifications, weekly availability
  and insurance, plus **15 customers**
- **~1,760 bookings** across eight weeks (far above the 50 required), with
  ~1,590 payments, ~1,300 ratings and a full welfare ledger
- Demand history **aggregated from those bookings**, so the forecast and the
  analytics can never contradict each other

Every dashboard figure — utilisation 69%, fairness 86/100, the electrical
shortage, the solar skill gap — falls out of this data. None of it is hardcoded
in a component.

---

## API

All endpoints are under `/api`. Errors always come back in one envelope:

```json
{ "error": { "code": "conflict", "message": "…", "details": null } }
```

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/auth/register` | Customers only; admin accounts are provisioned by the cooperative |
| `POST` | `/auth/login` | Identical message for unknown email and wrong password |
| `POST` | `/auth/demo-login` | One-click persona access |
| `GET` | `/auth/me`, `/auth/demo-accounts` | |
| `GET` | `/services`, `/zones`, `/skills` | Public catalogue |
| `GET` | `/workers`, `/workers/{id}` | Filter by service, zone, skill, availability, search |
| `GET` | `/workers/me`, `/workers/me/summary` | |
| `PATCH` | `/workers/me/availability` | |
| `POST` | `/bookings` | Description, explicit service, or both |
| `GET` | `/bookings`, `/bookings/{id}` | Scoped by role |
| `PATCH` | `/bookings/{id}/status` | Validated against the state machine |
| `POST` | `/ai/understand-request` | AI #1 |
| `POST` | `/matching`, `/matching/assign` | AI #2 |
| `GET` | `/forecast` | AI #3 |
| `GET` | `/workforce` | AI #4 and #5 |
| `GET` | `/welfare`, `/dashboard`, `/analytics` | |
| `POST` | `/payments`, `/ratings` | |
| `GET` | `/payments/{booking_id}/invoice` | |
| `GET`/`PATCH` | `/notifications` | |
| `GET`/`POST` | `/demo/state`, `/demo/reset`, `/demo/scenario/start` | |
| `GET` | `/health` | Reports database, AI configuration and warnings |

---

## Configuration

Secrets are read from the environment and never reach the browser bundle. See
`backend/.env.example` and `frontend/.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./nookr.db` | `postgresql+psycopg://…` in production |
| `JWT_SECRET` | dev-only placeholder | **Must be set** outside development |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | |
| `CORS_ORIGINS` | localhost dev ports | Comma-separated |
| `COOPERATIVE_TIMEZONE` | `Asia/Kolkata` | Decides when "today" starts for the dashboard and demand buckets |
| `AI_API_KEY` | *(empty)* | Optional. Empty means the rule engine is used, and the product still works fully |
| `AI_MODEL`, `AI_BASE_URL` | Anthropic defaults | |
| `DEMO_PASSWORD` | `demo1234` | The three demo accounts |
| `VITE_API_BASE_URL` | *(empty)* | Frontend only. Empty uses the dev proxy |

`/api/health` reports any misconfiguration — a default JWT secret, or SQLite
outside development — rather than failing silently.

---

## Testing

```bash
cd backend
python -m pytest -q
```

**43 tests**, run against a throwaway database seeded by the real seed script:

- **Auth** — demo login, password login, registration, duplicate emails, weak
  passwords, self-service admin refusal, role gates on every protected route
- **AI understanding** — the scripted request, emergencies, the
  I-don't-know case, empty input
- **Matching** — that fairness beats proximity and rating; that components sum
  to the final score; that uncertified workers are excluded from certified work
- **Forecasting / workforce / skill gaps** — method reporting, the electrical
  shortage, the solar gap, and that the projection declares itself a simulation
- **Booking rules** — every illegal transition, double payment, double rating,
  rating bounds, cross-customer access, ineligible allocation
- **Cooperative day** — that "completed today" uses local midnight, not UTC
- **End to end** — the full ten-step journey after a demo reset, including that
  the payment splits to exactly 560/40/20/30 and that the dashboard moves by
  exactly one job

Frontend:

```bash
cd frontend
npm run typecheck
```

```bash
npm run build
```

---

## Recording the demo

`demo/` contains a Playwright script that drives the real application and
produces `demo/output/nookr-demo.mp4` (1440x900, H.264, ~3¼ minutes) with
on-screen captions and a visible cursor. With both servers running:

```bash
cd demo && npm install && npx playwright install chromium && npm run record
```

See `demo/README.md`.

---

## Deployment

**Database — Supabase (or any managed PostgreSQL).** Take the connection string
and set `DATABASE_URL=postgresql+psycopg://…`. The schema and migrations are
dialect-neutral; nothing needs to change.

**Backend — Render.**

- Root directory `backend`
- Build: `pip install -r requirements.txt`
- Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment: `DATABASE_URL`, `JWT_SECRET` (long and random),
  `CORS_ORIGINS=https://your-frontend.vercel.app`, `ENVIRONMENT=production`,
  and `AI_API_KEY` only if you want the LLM path
- Seed once: `python -m app.db.seed --reset`

**Frontend — Vercel.**

- Root directory `frontend`
- Build: `npm run build`, output `dist`
- Environment: `VITE_API_BASE_URL=https://your-api.onrender.com`
- Add a rewrite so client-side routes resolve:

```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

Then set `CORS_ORIGINS` on the backend to the deployed frontend origin.

---

## Honest limitations

Stated up front, because a prototype that overclaims is worse than one that
doesn't.

- **Payments are simulated.** No payment gateway is integrated and no money
  moves. Every payment surface says so.
- **Locations are schematic.** Distances are haversine × a road factor, and the
  tracking view is a labelled diagram, not a live map. This is deliberate: no
  paid mapping API, and the demo works offline.
- **Forecasting is a transparent baseline**, not a learned model. With eight
  weeks of history that is both more accurate and more defensible than a deep
  model, and the method is reported in every response.
- **The workload projection is a simulation**, labelled as such everywhere.
- **SQLite is the local default** so the demo needs no services. PostgreSQL is
  the production target and the migrations run on both.
- **Voice input** uses the browser's own Web Speech API where available
  (Chrome, Edge, Safari) and falls back to typing everywhere else, with a
  message saying so.
- **Translations cover** navigation, the customer workflow, allocation, the
  worker portal, payment and feedback. Deeper analytics copy remains in English
  and falls back cleanly rather than showing missing keys.
