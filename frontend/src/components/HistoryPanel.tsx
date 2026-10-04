import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { StatusPill } from "../status";
import type { CheckRow } from "../types";
import Icon from "./Icon";

const SOURCE: Record<string, string> = { upload: "Upload", link: "Link", sample: "Sample", search: "Search" };

export default function HistoryPanel({ onOpen }: { onOpen: (id: string) => void }) {
  const [rows, setRows] = useState<CheckRow[] | null>(null);
  const [kind, setKind] = useState<"all" | "tender" | "search">("all");
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.history().then((r) => setRows(r.checks)).catch((e) => setError(e.message));
  }, []);

  const shown = useMemo(() => {
    const f = filter.toLowerCase();
    return (rows ?? []).filter((r) => (kind === "all" || r.kind === kind) &&
      (!f || r.title.toLowerCase().includes(f) || r.standards.some((s) => s.toLowerCase().includes(f))));
  }, [rows, kind, filter]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!rows) return <p className="muted">Loading past checks…</p>;

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>Past compliance checks</h2>
          <p className="muted">Every tender check and standards search, newest first. Open one to see the full result again.</p>
        </div>
      </div>
      <div className="toolbar">
        <div className="segmented segmented-light" role="group" aria-label="Type of check">
          {(["all", "tender", "search"] as const).map((k) => (
            <button key={k} className={kind === k ? "on" : ""} onClick={() => setKind(k)}>
              {k === "all" ? `All (${rows.length})` : k === "tender" ? "Tenders" : "Searches"}
            </button>
          ))}
        </div>
        <input type="search" placeholder="Filter by document, query or IS number" value={filter} onChange={(e) => setFilter(e.target.value)} />
      </div>
      {shown.length === 0 ? (
        <p className="muted">No checks match.</p>
      ) : (
        <div className="table-wrap">
          <table className="table history">
            <thead><tr><th>When</th><th>Checked</th><th>Result</th><th>Indian Standards</th><th /></tr></thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id}>
                  <td className="nowrap" data-label="When" title={r.time}>{new Date(r.time).toLocaleString()}</td>
                  <td data-label="Checked">
                    <span className="hist-title"><Icon name={r.kind === "tender" ? "file" : "search"} size={15} /> {r.title}</span>
                    <span className="muted small">
                      {SOURCE[r.source] ?? r.source}
                      {r.kind === "tender" && ` · ${r.items ?? 0} items · ${r.issues ?? 0} issues`}
                    </span>
                  </td>
                  <td data-label="Result">{r.status ? <StatusPill status={r.status} label={r.status_label} size="sm" /> : <span className="muted">–</span>}</td>
                  <td data-label="Standards">
                    {r.standards.length ? r.standards.map((s) => <span key={s} className="tag">{s}</span>) : <span className="muted">–</span>}
                  </td>
                  <td className="nowrap">
                    <button className="btn btn-secondary btn-sm" onClick={() => onOpen(r.id)} disabled={!r.reopen}
                      title={r.reopen ? "" : "Result not saved for this older check"}>Open</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
