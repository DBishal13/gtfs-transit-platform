import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { isBackendConfigured } from "../lib/apiClient";
import { useAuthContext } from "../lib/AuthContext";

export default function Login() {
  const { login, signup } = useAuthContext();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!isBackendConfigured()) {
    return <div className="page empty-state">Dispatch backend isn't configured for this deployment.</div>;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "signin") {
        await login(email, password);
      } else {
        await signup(orgName, email, password);
      }
      navigate("/");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page" style={{ maxWidth: 420 }}>
      <div className="card">
        <h2>{mode === "signin" ? "Sign in" : "Create an account"}</h2>
        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "signup" && (
            <label>
              Organization name
              <input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
            </label>
          )}
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </label>
          {error && <p style={{ color: "var(--error)" }}>{error}</p>}
          <button type="submit" disabled={busy}>
            {busy ? "…" : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>
        <button
          className="link-button"
          style={{ marginTop: "0.75rem" }}
          onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
        >
          {mode === "signin" ? "Need an account? Create one" : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
