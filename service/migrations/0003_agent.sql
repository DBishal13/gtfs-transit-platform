-- Agent conversation persistence: a full audit trail of every turn, including which
-- tools were called with what arguments. This is a documented mitigation, not just
-- logging for its own sake — see service/app/services/agent/safety.py: even a partially
-- successful prompt-injection attempt against the agent stays visible after the fact.

CREATE TABLE IF NOT EXISTS agent_conversations (
  conversation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES orgs(org_id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(user_id),
  feed_id text NOT NULL REFERENCES feeds(feed_id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_conversations_org_idx ON agent_conversations (org_id);

CREATE TABLE IF NOT EXISTS agent_messages (
  message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES agent_conversations(conversation_id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  content jsonb NOT NULL,  -- the turn's plain question / final answer text
  tool_calls jsonb,        -- [{tool_name, arguments, result_summary}, ...] made during this turn
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_messages_conversation_idx
  ON agent_messages (conversation_id, created_at);
