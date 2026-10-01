import { useEffect, useState } from "react";
import { api } from "../api";
import type { RecommendResponse } from "../types";
import ResultCard from "./ResultCard";

const EXAMPLES = [
  "TMT reinforcement bars Fe 500D for building construction",
  "LED street light 90 W, IP66, aluminium housing",
  "PVC insulated copper house wiring cable 1.5 sq mm",
  "1000 litre overhead water storage tank",
  "बिजली के तार घरेलू वायरिंग के लिए",
  "Housekeeping services for office building",
];

export default function RecommendPanel({ lang, initialQuery = "" }: { lang: "en" | "hi"; initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [data, setData] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (q = query) => {
    if (q.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      setData(await api.recommend(q.trim(), lang));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (initialQuery) run(initialQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const a = data?.attributes;
  return (
    <div className="stack">
      <section className="card">
        <h2>Describe the product or paste a specification</h2>
        <p className="muted">English, Hindi and other Indian languages are accepted. Citing an IS number (for example IS 694:1990) also checks its edition.</p>
        <form onSubmit={(e) => { e.preventDefault(); run(); }}>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            maxLength={5000}
            placeholder="e.g. Armoured XLPE aluminium power cable, 3.5 core, 95 sq mm, 1.1 kV"
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run(); }}
          />
          <div className="form-row">
            <div className="examples">
              <span className="muted small">Examples:</span>
              {EXAMPLES.map((ex) => (
                <button type="button" key={ex} className="chip" onClick={() => { setQuery(ex); run(ex); }}>{ex}</button>
              ))}
            </div>
            <button className="btn btn-primary" disabled={busy || query.trim().length < 3}>
              {busy ? "Searching…" : "Find standards"}
            </button>
          </div>
        </form>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      {data && (
        <>
          <section className="meta-row">
            <span><strong>Language detected:</strong> {data.detected_language.name}</span>
            {a && (a.materials.length > 0 || a.quantities.length > 0 || a.grades.length > 0) && (
              <span><strong>Attributes:</strong> {[...a.materials, ...a.grades, ...a.quantities].join(" · ")}</span>
            )}
            {data.expanded_terms.length > 0 && <span><strong>Glossary terms:</strong> {data.expanded_terms.join(", ")}</span>}
            <span className="muted">Retrieval: {data.retrieval_mode}</span>
          </section>

          {data.abstained ? (
            <div className="alert alert-info">
              <strong>No applicable Indian Standard found.</strong> {data.abstain_reason}
            </div>
          ) : (
            <div className="stack">
              {data.results.map((r, i) => (
                <ResultCard key={`${data.request_id}-${r.standard.id}`} rank={i + 1} rec={r} requestId={data.request_id} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
