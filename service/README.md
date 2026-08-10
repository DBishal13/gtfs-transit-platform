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

**Phase 2 of 6** — database foundation, geo REST endpoints, and auth/multi-tenancy. No
geocoding/reachability yet (Phase 3), no LLM agent yet (Phase 4), no frontend integration yet
(Phase 5), no deployment/observability polish yet (Phase 6).

Every `/geo/*` request now requires either a JWT (`Authorization: Bearer <token>`, issued by
`/auth/login`) or an API key (`X-API-Key: <key>`, minted via `/auth/api-keys`), and is rejected
with 403 unless the requested `feed_id` is public, owned by the caller's org, or explicitly
granted to it (`service/app/services/tenancy_service.py::resolve_visible_feed_ids`).

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
