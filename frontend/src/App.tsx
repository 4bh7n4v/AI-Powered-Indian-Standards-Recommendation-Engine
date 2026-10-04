import { useEffect, useState } from "react";
import { api } from "./api";
import type { Health, RecommendResponse, TenderResponse } from "./types";
import Header from "./components/Header";
import Icon, { type IconName } from "./components/Icon";
import Dashboard from "./components/Dashboard";
import RecommendPanel from "./components/RecommendPanel";
import TenderPanel from "./components/TenderPanel";
import HistoryPanel from "./components/HistoryPanel";
import RegistryPanel from "./components/RegistryPanel";
import ApiPanel from "./components/ApiPanel";

const TABS: { id: string; label: string; icon: IconName }[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "tender", label: "Check a Tender", icon: "tender" },
  { id: "recommend", label: "Find Standards", icon: "search" },
  { id: "history", label: "Past Checks", icon: "history" },
  { id: "registry", label: "Standards Registry", icon: "book" },
  { id: "api", label: "Portal Integration", icon: "plug" },
];
export type TabId = "dashboard" | "tender" | "recommend" | "history" | "registry" | "api";

const params = new URLSearchParams(window.location.search);
const initialTab = ((TABS.find((t) => t.id === params.get("tab"))?.id) ??
  (params.get("q") ? "recommend" : params.get("sample") ? "tender" : "dashboard")) as TabId;

export default function App() {
  const [tab, setTab] = useState<TabId>(initialTab);
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [health, setHealth] = useState<Health | null>(null);
  // The latest result of each panel survives tab switches; `openSeq` remounts a panel when a past check is opened.
  const [lastTender, setLastTender] = useState<TenderResponse | undefined>();
  const [lastSearch, setLastSearch] = useState<RecommendResponse | undefined>();
  const [openSeq, setOpenSeq] = useState(0);
  const [openError, setOpenError] = useState<string | null>(null);
  const [deepLinkUsed, setDeepLinkUsed] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const go = (t: TabId) => {
    setTab(t);
    window.scrollTo({ top: 0 });
  };

  const openCheck = async (id: string) => {
    setOpenError(null);
    try {
      const data = await api.check(id);
      setDeepLinkUsed(true);
      setOpenSeq((n) => n + 1);
      if ("items" in data) {
        setLastTender(data);
        go("tender");
      } else {
        setLastSearch(data);
        go("recommend");
      }
    } catch (e) {
      setOpenError((e as Error).message);
    }
  };

  return (
    <div className="page">
      <Header health={health} lang={lang} onLang={setLang} />
      <nav className="nav" aria-label="Sections">
        <div className="container nav-inner" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "nav-item active" : "nav-item"}
              onClick={() => go(t.id as TabId)}>
              <Icon name={t.icon} size={16} />
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      {health && !health.data_verified && (
        <div className="demo-strip">
          <div className="container">
            <Icon name="info" size={14} /> Demo data: {health.standards} sample standards in 5 product domains, as of {health.data_as_of}.
            Verify editions and certification on the BIS Standards Portal before use in a real tender.
          </div>
        </div>
      )}
      <main className="container main">
        {openError && <div className="alert alert-error">{openError}</div>}
        {tab === "dashboard" && <Dashboard onNavigate={go} onOpen={openCheck} />}
        {tab === "tender" && (
          <TenderPanel
            key={`tender-${openSeq}`}
            lang={lang}
            initial={lastTender}
            onResult={(d) => { setLastTender(d); setDeepLinkUsed(true); }}
            autoSample={deepLinkUsed ? "" : params.get("sample") === "1" ? "01" : (params.get("sample") ?? "")}
          />
        )}
        {tab === "recommend" && (
          <RecommendPanel
            key={`search-${openSeq}`}
            lang={lang}
            initial={lastSearch}
            onResult={(d) => { setLastSearch(d); setDeepLinkUsed(true); }}
            initialQuery={deepLinkUsed ? "" : (params.get("q") ?? "")}
          />
        )}
        {tab === "history" && <HistoryPanel onOpen={openCheck} />}
        {tab === "registry" && <RegistryPanel />}
        {tab === "api" && <ApiPanel />}
      </main>
      <footer className="footer">
        <div className="container">
          <p>Smart India Hackathon prototype for Problem Statement 26108 (Department of Consumer Affairs). Not an official Government of India service.</p>
          <p className="muted">
            Standards data is an illustrative seed{health ? ` (as of ${health.data_as_of})` : ""}. Verify every edition,
            amendment and certification requirement on the BIS Standards Portal before use in a tender.
          </p>
        </div>
      </footer>
    </div>
  );
}
