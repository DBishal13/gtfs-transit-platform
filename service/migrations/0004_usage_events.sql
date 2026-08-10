-- Basic per-org usage metering — primarily for LLM token accounting on /agent/ask
-- (service/app/routers/agent.py), which is the only endpoint expensive enough to be
-- worth metering individually right now. Explicitly not wired to any billing/invoicing —
-- see service/README.md's out-of-scope list.

CREATE TABLE IF NOT EXISTS api_usage_events (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid REFERENCES orgs(org_id) ON DELETE CASCADE,
  route text NOT NULL,
  method text NOT NULL,
  status_code int NOT NULL,
  latency_ms int NOT NULL,
  llm_input_tokens int,
  llm_output_tokens int,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS api_usage_events_org_idx ON api_usage_events (org_id, created_at);
