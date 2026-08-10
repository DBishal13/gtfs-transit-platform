# Backend service

A hosted FastAPI backend — a **third track** alongside the two documented in
[`../docs/architecture.md`](../docs/architecture.md) (the static export pipeline deployed to
GitHub Pages, and the local-only PostGIS deep-dive). Neither of those tracks is touched by this
one: the static app still builds and deploys exactly as before, with zero runtime dependency on
this service.

This service exists because a real natural-language agent and real location/geo queries need
things a static site fundamentally cannot provide: a live database to query, authentication, and
per-tenant data isolation. See the plan this was built from for the full design rationale
(constrained-tool-calling agent architecture, multi-tenancy model, provider-agnostic LLM layer).

## Status

**Phase 6 of 6 (complete)** — database foundation, geo REST endpoints, auth/multi-tenancy,
geocoding, reachability, the natural-language agent, the frontend Dispatch console
(`app/src/components/agent/DispatchConsole.tsx`), and this phase's deployment/observability
polish: rate limiting, structured logging, usage metering, and a Dockerfile/Fly.io config. What's
still a manual step for you: actually provisioning a Fly.io app and a hosted Postgres (e.g. Neon)
— see "Deploying" below.

Every `/geo/*` and `/agent/*` request requires either a JWT (`Authorization: Bearer <token>`,
issued by `/auth/login`) or an API key (`X-API-Key: <key>`, minted via `/auth/api-keys`), and is
rejected with 403 unless the requested `feed_id` is public, owned by the caller's org, or
explicitly granted to it (`service/app/services/tenancy_service.py::resolve_visible_feed_ids`).

`POST /geo/geocode` resolves free-text address/place queries to coordinates (Nominatim by
default; provider-swappable — see `service/app/services/geocoding_service.py`).
`POST /geo/reachability` returns a **schedule-based walk + one-transit-hop approximation** of
what's reachable in N minutes — not true multimodal routing; see the docstring in
`service/app/services/reachability_service.py` for exactly what's simplified and why.

`POST /agent/ask` answers natural-language questions about a feed. The LLM (Anthropic or OpenAI,
config-selected — see `service/app/services/agent/llm_provider.py`) never writes or executes SQL;
it can only call a fixed, Pydantic-validated set of tools (`service/app/services/agent/tools.py`)
that wrap the exact same `geo_service`/`geocoding_service`/`reachability_service` functions the
REST endpoints use. `org_id`/`feed_id` are always injected server-side into every tool call, never
taken from the LLM's proposed arguments — see `service/app/services/agent/safety.py` for the full
list of prompt-injection mitigations and `service/tests/test_agent_tools_safety.py` for the
adversarial tests. Every conversation turn (including the tool-call trace) is persisted for audit
via `service/app/services/agent/store.py`.

Every `/geo/*` and `/agent/ask` request is per-org rate-limited (in-memory sliding window, see
`service/app/middleware/rate_limit.py`; `Settings.rate_limit_default_per_min`, default 60/min).
Every request is logged as one structured JSON line (`service/app/middleware/request_context.py`)
with a `request_id` also returned as an `X-Request-ID` response header. `/agent/ask` additionally
records an `api_usage_events` row per call (route, latency, LLM token counts — see
`service/app/services/usage_service.py`), enough for a simple "usage this month" query per org;
not wired to any billing.

## Local development

```bash
# from the repo root
pip install -e ".[service,dev]"
docker compose up -d          # starts the same postgis/postgis:16-3.4 used by pipeline/postgis/
python -m service.migrations.runner   # applies pipeline/postgis/schema.sql + service/migrations/*.sql
uvicorn service.app.main:app --reload
# Swagger UI: http://localhost:8000/docs

# load a real feed for local testing (reuses the existing pipeline/postgis loader):
python -m pipeline.postgis.load load broward-bct

# create an account, then use the returned access_token as a Bearer token (or mint an
# API key via POST /auth/api-keys once logged in):
curl -X POST localhost:8000/auth/signup -H 'Content-Type: application/json' \
  -d '{"org_name":"Acme Transit","email":"you@example.com","password":"correct horse battery"}'
```

## Tests

Backend tests live under `service/tests/`, not `tests/` — the root `tests/` package's
`pytest -q` (used by CI's `pipeline-tests` job) never installs the `service` extra, so keeping
them separate avoids breaking that job. Tests requiring a database skip automatically (rather
than failing) if one isn't reachable.

```bash
pytest service/tests -q
```

## Cost

Two ways to run this, at two very different price points — pick based on whether you need
it publicly reachable or just runnable on demand.

**Option A — local only, $0, no card anywhere.** `docker compose up` + `uvicorn` (see
"Local development" above) runs the full stack — Postgres/PostGIS, the API, and (pointed
at it) the frontend — entirely on your machine. Nothing is publicly reachable; this is
what you'd use to demo the app to yourself or on a screen-share. The one piece this can't
avoid: an LLM API call (Anthropic/OpenAI) still costs real tokens the moment `/agent/ask`
is actually invoked with a real key configured — everything else (signup/login, geo
queries, the console UI) works with zero API key and zero cost.

**Option B — hosted (Fly.io + Neon), for a real public URL.** *Correction from an earlier
claim in this repo's history: Fly.io no longer has a free tier* (removed in 2024) — new
accounts get a small one-time trial credit, then a credit card is required, and the
cheapest always-on app runs roughly $2–5/month. Neon's free tier (Postgres/PostGIS) is
genuinely free at this project's scale and doesn't need a card. Either way, the LLM API
itself (Anthropic or OpenAI) is pay-as-you-go with only a small one-time free credit on
signup — that's the one recurring cost neither hosting option avoids.

## Deploying (Option B — hosted)

Nothing below runs automatically — it's the manual provisioning step `.github/workflows/deploy-service.yml`
is written to wait for (its `deploy` job is skipped, not failed, until `FLY_API_TOKEN` exists).

1. **Database**: create a hosted Postgres with the PostGIS extension available — [Neon](https://neon.tech)
   (recommended: branching, generous free tier, zero adaptation needed for the hand-written SQL
   already in `pipeline/postgis/`) or [Supabase](https://supabase.com) both work. Note the
   connection string.
2. **Fly.io app**: `fly launch --no-deploy` from the repo root (uses `fly.toml` /
   `service/Dockerfile`; rename the placeholder `app` name in `fly.toml` to whatever it assigns).
   Requires a credit card on file — see "Cost" above.
3. **Secrets** (never commit these): `fly secrets set DATABASE_URL=<neon connection string>
   JWT_SECRET_KEY=<a real random secret> ANTHROPIC_API_KEY=<or OPENAI_API_KEY, matching LLM_PROVIDER>
   CORS_ORIGINS='["https://<your-username>.github.io"]'`
4. **First deploy**: `fly deploy` (runs `service/migrations/runner.py` automatically as the
   `release_command` in `fly.toml` before each deploy).
5. **CI/CD**: add `FLY_API_TOKEN` (from `fly tokens create deploy`) as a GitHub Actions repo
   secret — `deploy-service.yml`'s `deploy` job then runs on every push to `main` touching
   `service/`/`pipeline/`.
6. **Frontend**: set `VITE_API_BASE_URL` to the deployed Fly app's URL wherever `app/` is built
   (a repo variable/secret in `.github/workflows/deploy.yml`, or a local `.env` for `npm run dev`)
   — this is what makes the Dispatch console and sign-in actually appear.

## Explicitly out of scope (portfolio-grade bar, not a commercial launch)

Billing/Stripe integration, SOC2 controls, formal Terms of Service, SSO/SAML, distributed
rate-limiting infrastructure (Redis) unless traffic actually needs it, and a usage-dashboard UI
(the underlying `api_usage_events` table exists; a dashboard over it does not). Per-API-key rate
limits (the `api_keys.rate_limit_per_min` column) are stored but not yet enforced — every request
is currently limited uniformly per org via `Settings.rate_limit_default_per_min`.
