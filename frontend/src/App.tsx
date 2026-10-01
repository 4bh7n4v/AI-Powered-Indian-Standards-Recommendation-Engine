import { useEffect, useState } from "react";
import { api } from "./api";
import type { Health } from "./types";
import Header from "./components/Header";
import RecommendPanel from "./components/RecommendPanel";
import TenderPanel from "./components/TenderPanel";
import RegistryPanel from "./components/RegistryPanel";
import ApiPanel from "./components/ApiPanel";

const TABS = [
  { id: "recommend", label: "Find Standards" },
  { id: "tender", label: "Tender Health Check" },
  { id: "registry", label: "Standards Registry" },
  { id: "api", label: "Portal Integration" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const params = new URLSearchParams(window.location.search);
const initialTab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "recommend") as TabId;

export default function App() {
  const [tab, setTab] = useState<TabId>(initialTab);
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="page">
      <Header health={health} lang={lang} onLang={setLang} />
      <nav className="tabs" role="tablist">
        <div className="container tabs-inner">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      <main className="container main">
        {tab === "recommend" && <RecommendPanel lang={lang} initialQuery={params.get("q") ?? ""} />}
        {tab === "tender" && <TenderPanel lang={lang} autoSample={params.get("sample") === "1" ? "01" : (params.get("sample") ?? "")} />}
        {tab === "registry" && <RegistryPanel />}
        {tab === "api" && <ApiPanel />}
      </main>
      <footer className="footer">
        <div className="container">
          <p>
            Smart India Hackathon prototype for Problem Statement 26108 (Department of Consumer Affairs). Not an official
            Government of India service.
          </p>
          <p className="muted">
            Standards data is an illustrative seed{health ? ` (as of ${health.data_as_of})` : ""}. Verify every edition,
            amendment and certification requirement on the BIS Standards Portal before use in a tender.
          </p>
        </div>
      </footer>
    </div>
  );
}
