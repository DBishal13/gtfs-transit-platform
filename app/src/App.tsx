import { HashRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./lib/AuthContext";
import { FeedProvider } from "./lib/FeedContext";
import Layout from "./routes/Layout";
import MapExplorer from "./routes/MapExplorer";
import Headway from "./routes/Headway";
import Coverage from "./routes/Coverage";
import DataQuality from "./routes/DataQuality";
import Compare from "./routes/Compare";
import Login from "./routes/Login";

// HashRouter, not BrowserRouter: GitHub Pages serves static files with no
// server-side rewrite rule, so client-side routes must live in the URL hash
// to survive a hard refresh/deep link on a project subpath.
//
// AuthProvider wraps unconditionally (like FeedProvider) — it's inert when
// VITE_API_BASE_URL is unset (see apiClient.ts::isBackendConfigured), so this doesn't
// affect the static GitHub Pages build's behavior.
export default function App() {
  return (
    <FeedProvider>
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<MapExplorer />} />
              <Route path="headway" element={<Headway />} />
              <Route path="coverage" element={<Coverage />} />
              <Route path="quality" element={<DataQuality />} />
              <Route path="compare" element={<Compare />} />
              <Route path="login" element={<Login />} />
            </Route>
          </Routes>
        </HashRouter>
      </AuthProvider>
    </FeedProvider>
  );
}
