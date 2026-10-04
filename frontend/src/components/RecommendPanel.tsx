import { useEffect, useState } from "react";
import { api } from "../api";
import type { RecommendResponse } from "../types";
import Icon from "./Icon";
import ResultCard from "./ResultCard";

const EXAMPLES = [
  "TMT reinforcement bars Fe 500D for building construction",
  "LED street light 90 W, IP66, aluminium housing",
  "PVC insulated copper house wiring cable 1.5 sq mm",
  "1000 litre overhead water storage tank",
  "बिजली के तार घरेलू वायरिंग के लिए",
  "Housekeeping services for office building",
];

interface Props {
  lang: "en" | "hi";
  initialQuery?: string;
  initial?: RecommendResponse;
  onResult?: (d: RecommendResponse) => void;
}

export default function RecommendPanel({ lang, initialQuery = "", initial, onResult }: Props) {
  const [query, setQuery] = useState(initial?.query ?? initialQuery);
  const [data, setData] = useState<RecommendResponse | null>(initial ?? null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (q = query) => {
    if (q.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.recommend(q.trim(), lang);
      setData(d);
      onResult?.(d);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (initialQuery && !initial) run(initialQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const a = data?.attributes;
  return (
    <div className="stack">
      <section className="card">
        <h2>Find the standards for a product</h2>
        <p className="muted">Describe the product or paste a specification. English, Hindi and other Indian languages work. Citing an IS number (for example IS 694:1990) also checks its edition.</p>
        <form onSubmit={(e) => { e.preventDefault(); run(); }}>
          <div className="search-box">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              maxLength={5000}
              placeholder="e.g. Armoured XLPE aluminium power cable, 3.5 core, 95 sq mm, 1.1 kV"
              onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run(); }}
            />
            <button className="btn btn-primary" disabled={busy || query.trim().length < 3}>
              <Icon name="search" size={16} /> {busy ? "Searching…" : "Find standards"}
            </button>
          </div>
          <div className="examples">
            <span className="muted small">Try:</span>
            {EXAMPLES.map((ex) => (
              <button type="button" key={ex} className="chip" onClick={() => { setQuery(ex); run(ex); }}>{ex}</button>
            ))}
          </div>
        </form>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      {data && (
        <>
          <section className="meta-row">
            <span><b>Language:</b> {data.detected_language.name}</span>
            {a && (a.materials.length > 0 || a.quantities.length > 0 || a.grades.length > 0) && (
              <span><b>Read from text:</b> {[...a.materials, ...a.grades, ...a.quantities].join(" · ")}</span>
            )}
            {data.expanded_terms.length > 0 && <span><b>Also searched:</b> {data.expanded_terms.join(", ")}</span>}
            <span className="muted" title="Retrieval method">{data.retrieval_mode}</span>
          </section>

          {data.abstained ? (
            <section className="card notsure">
              <span className="notsure-icon"><Icon name="help" size={28} /></span>
              <div>
                <h3>No confident match – check manually</h3>
                <p>{data.abstain_reason}</p>
                <p className="muted small">
                  The engine would rather say "I don't know" than suggest a wrong standard. Services usually have no Indian Standard.
                  For goods, name the product and its material, or cite an IS number.
                </p>
              </div>
            </section>
          ) : (
            <div className="stack-sm">
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
