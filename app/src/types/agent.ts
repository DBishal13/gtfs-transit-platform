// Mirrors service/app/schemas/agent.py and service/app/schemas/auth.py by hand — no
// shared runtime between the Python backend and this TypeScript frontend, same
// hand-kept-in-sync convention as dataContract.ts mirrors manifest.schema.json.

export interface SignupRequest {
  org_name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AskRequest {
  feed_id: string;
  question: string;
  conversation_id?: string | null;
}

export interface MapPoint {
  lon: number;
  lat: number;
  label?: string | null;
}

export interface MapPayload {
  points: MapPoint[];
}

export interface ToolTraceEntry {
  tool_name: string;
  arguments: Record<string, unknown>;
  result_summary: string;
}

export interface AskResponse {
  conversation_id: string;
  answer: string;
  map_payload: MapPayload;
  tool_trace: ToolTraceEntry[];
}
