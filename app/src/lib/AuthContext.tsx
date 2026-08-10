import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  clearSession,
  getStoredRefreshToken,
  isBackendConfigured,
  login as apiLogin,
  refreshAccessToken,
  signup as apiSignup,
  setTokens,
} from "./apiClient";

interface AuthContextValue {
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (orgName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // On mount, try to restore a session from the persisted refresh token — the access
  // token itself is memory-only and doesn't survive a reload (see apiClient.ts).
  useEffect(() => {
    if (!isBackendConfigured()) {
      setLoading(false);
      return;
    }
    const stored = getStoredRefreshToken();
    if (!stored) {
      setLoading(false);
      return;
    }
    refreshAccessToken(stored)
      .then(() => setIsAuthenticated(true))
      .catch(() => clearSession())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const tokens = await apiLogin({ email, password });
    setTokens(tokens);
    setIsAuthenticated(true);
  }

  async function signup(orgName: string, email: string, password: string) {
    const tokens = await apiSignup({ org_name: orgName, email, password });
    setTokens(tokens);
    setIsAuthenticated(true);
  }

  function logout() {
    clearSession();
    setIsAuthenticated(false);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within an AuthProvider");
  return ctx;
}
