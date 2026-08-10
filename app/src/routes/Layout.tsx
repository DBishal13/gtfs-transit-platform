import { NavLink, Outlet } from "react-router-dom";
import { isBackendConfigured } from "../lib/apiClient";
import { useAuthContext } from "../lib/AuthContext";
import { useFeedContext } from "../lib/FeedContext";

function AuthStatus() {
  const { isAuthenticated, logout } = useAuthContext();
  if (!isBackendConfigured()) return null;
  return isAuthenticated ? (
    <button className="link-button" onClick={logout}>
      Sign out
    </button>
  ) : (
    <NavLink to="/login" className={({ isActive }) => (isActive ? "active" : "")}>
      Sign in
    </NavLink>
  );
}

function FeedPicker() {
  const { manifest, selectedFeedId, setSelectedFeedId, loading } = useFeedContext();

  if (loading) return null;
  if (!manifest || manifest.feeds.length === 0) {
    return <span className="feed-picker">No feeds available</span>;
  }

  return (
    <span className="feed-picker">
      <select
        value={selectedFeedId ?? ""}
        onChange={(e) => setSelectedFeedId(e.target.value)}
        aria-label="Select transit feed"
      >
        {manifest.feeds.map((feed) => (
          <option key={feed.id} value={feed.id}>
            {feed.name}
          </option>
        ))}
      </select>
    </span>
  );
}

export default function Layout() {
  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-nav__brand">Transit Data Platform</span>
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Map
        </NavLink>
        <NavLink to="/headway" className={({ isActive }) => (isActive ? "active" : "")}>
          Frequency
        </NavLink>
        <NavLink to="/coverage" className={({ isActive }) => (isActive ? "active" : "")}>
          Coverage
        </NavLink>
        <NavLink to="/quality" className={({ isActive }) => (isActive ? "active" : "")}>
          Data Quality
        </NavLink>
        <NavLink to="/compare" className={({ isActive }) => (isActive ? "active" : "")}>
          Compare
        </NavLink>
        <FeedPicker />
        <AuthStatus />
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
