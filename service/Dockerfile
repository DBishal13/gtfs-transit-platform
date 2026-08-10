# Container image for the backend service (service/) — not used by the static GitHub
# Pages track (pipeline/ + app/); see docs/architecture.md for how the tracks relate.
#
# Single-stage: psycopg[binary] ships a prebuilt wheel, so there's no compiler toolchain
# or intermediate build artifact that a multi-stage build would let us discard here.
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY pipeline ./pipeline
COPY service ./service

RUN pip install --no-cache-dir -e ".[service]"

EXPOSE 8080

CMD ["uvicorn", "service.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
