"""FastAPI app factory for the gtfs-transit-platform backend service.

This is a new, hosted backend track alongside the two existing tracks documented in
docs/architecture.md: the static export pipeline (GitHub Pages, zero server) and the
local-only PostGIS deep-dive. This service powers location/geo queries (Phase 1+) and,
from Phase 4, the natural-language agent. It is entirely additive — the static app and
its deploy workflow are untouched and unaffected by this service's existence.

Run locally with:
    uvicorn service.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service.app.config import get_settings
from service.app.routers import agent, auth, feeds, geo, health, orgs


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GTFS Transit Platform API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(orgs.router)
    app.include_router(feeds.router)
    app.include_router(geo.router)
    app.include_router(agent.router)

    return app


app = create_app()
