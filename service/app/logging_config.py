"""Structured JSON request logging for the backend service.

Extends the plain-text convention in pipeline/utils/logging.py: that logger is fine for a
local CLI run where a human reads stdout directly, but a hosted service benefits from
JSON lines a log platform (Fly.io's log shipping, etc.) can actually query/filter on.
Kept as a separate, additive convention rather than changing pipeline/utils/logging.py,
since the pipeline's local-CLI use case is unaffected by this service's needs.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
