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

**Phase 4 of 6** — database foundation, geo REST endpoints, auth/multi-tenancy, geocoding,
reachability, and the natural-language agent. No frontend integration yet (Phase 5), no
deployment/observability polish yet (Phase 6).

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

## Explicitly out of scope (portfolio-grade bar, not a commercial launch)

Billing/Stripe integration, SOC2 controls, formal Terms of Service, SSO/SAML, distributed
rate-limiting infrastructure (Redis) unless traffic actually needs it, and a usage-dashboard UI
(the underlying `api_usage_events` data will exist from Phase 6; a dashboard over it does not).
