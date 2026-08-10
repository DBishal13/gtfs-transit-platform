// Thin typed fetch wrapper for the backend service (service/), mirroring manifest.ts's
// small-wrapper style rather than pulling in a full HTTP client dependency.
//
// VITE_API_BASE_URL is a build-time env var — it's never set in
// .github/workflows/deploy.yml, so isBackendConfigured() is false in the static GitHub
// Pages build and every consumer of this module (AuthContext, DispatchConsole, Login)
// renders nothing rather than attempting a request.
import type { AskRequest, AskResponse, LoginRequest, SignupRequest, TokenResponse } from "../types/agent";

const API_BASE = import.meta.env.VITE_API_BASE_URL;
const REFRESH_TOKEN_KEY = "gtp_refresh_token";

// Access token lives in memory only (lost on page reload, restored via a silent
// /auth/refresh call in AuthContext); the refresh token is persisted to localStorage.
// This is a documented tradeoff vs. an httpOnly cookie, which would require the frontend
// and backend to share an origin — not the case for a GitHub-Pages-hosted SPA talking to
// an independently-hosted API.
let accessToken: string | null = null;

export function isBackendConfigured(): boolean {
  return Boolean(API_BASE);
}

export function setTokens(tokens: TokenResponse): void {
  accessToken = tokens.access_token;
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearSession(): void {
  accessToken = null;
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE) throw new Error("Backend is not configured (VITE_API_BASE_URL unset)");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401) {
    clearSession();
    throw new Error("Session expired — please sign in again");
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export function signup(body: SignupRequest): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/signup", { method: "POST", body: JSON.stringify(body) });
}

export function login(body: LoginRequest): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) });
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenResponse> {
  const tokens = await apiFetch<TokenResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  setTokens(tokens);
  return tokens;
}

export function askAgent(body: AskRequest): Promise<AskResponse> {
  return apiFetch<AskResponse>("/agent/ask", { method: "POST", body: JSON.stringify(body) });
}
