import { HashRouter, Route, Routes } from "react-router-dom";
import { FeedProvider } from "./lib/FeedContext";
import Layout from "./routes/Layout";
import MapExplorer from "./routes/MapExplorer";
import Headway from "./routes/Headway";
import Coverage from "./routes/Coverage";
import DataQuality from "./routes/DataQuality";
import Compare from "./routes/Compare";

// HashRouter, not BrowserRouter: GitHub Pages serves static files with no
// server-side rewrite rule, so client-side routes must live in the URL hash
// to survive a hard refresh/deep link on a project subpath.
export default function App() {
  return (
    <FeedProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<MapExplorer />} />
            <Route path="headway" element={<Headway />} />
            <Route path="coverage" element={<Coverage />} />
            <Route path="quality" element={<DataQuality />} />
            <Route path="compare" element={<Compare />} />
          </Route>
        </Routes>
      </HashRouter>
    </FeedProvider>
  );
}
