-- Multi-tenancy: orgs / users / api_keys / feed_grants, layered on top of the existing
-- feed_id-scoping convention (every GTFS table already carries feed_id; that convention
-- is unchanged). A feed's owner_org_id + is_public determine default visibility;
-- feed_grants adds explicit cross-org sharing. See
-- service/app/services/tenancy_service.py::resolve_visible_feed_ids for the query that
-- turns this schema into the actual tenant-isolation boundary every geo/agent query must
-- pass through.
--
-- gen_random_uuid() is built into Postgres core as of v13 (no pgcrypto extension needed).

ALTER TABLE feeds ADD COLUMN IF NOT EXISTS owner_org_id uuid;
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS is_public boolean NOT NULL DEFAULT true;

CREATE TABLE IF NOT EXISTS orgs (
  org_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text UNIQUE NOT NULL,
  plan text NOT NULL DEFAULT 'free', -- label only; no billing logic behind it (out of scope)
  created_at timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'feeds_owner_org_fk'
  ) THEN
    ALTER TABLE feeds ADD CONSTRAINT feeds_owner_org_fk
      FOREIGN KEY (owner_org_id) REFERENCES orgs(org_id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS users (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES orgs(org_id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL, -- argon2id, see service/app/services/auth_service.py
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  created_at timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz
);

CREATE TABLE IF NOT EXISTS api_keys (
  api_key_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES orgs(org_id) ON DELETE CASCADE,
  name text NOT NULL,
  key_prefix text NOT NULL,   -- shown in UI for identification, e.g. "gtp_live_ab12cd34"
  key_hash text NOT NULL,     -- sha256 of the full secret; the secret itself is never stored
  scopes text[] NOT NULL DEFAULT '{}',
  rate_limit_per_min int NOT NULL DEFAULT 60,
  created_by uuid REFERENCES users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);
CREATE INDEX IF NOT EXISTS api_keys_org_idx ON api_keys (org_id);
CREATE UNIQUE INDEX IF NOT EXISTS api_keys_hash_idx ON api_keys (key_hash) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS feed_grants (
  org_id uuid NOT NULL REFERENCES orgs(org_id) ON DELETE CASCADE,
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  granted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, feed_id)
);
