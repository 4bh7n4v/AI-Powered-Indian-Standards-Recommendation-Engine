import { useEffect, useState } from "react";
import { api } from "../api";
import { STATUS, StatusPill, timeAgo } from "../status";
import type { CheckRow, Stats } from "../types";
import type { TabId } from "../App";
import Icon from "./Icon";

interface Props {
  onNavigate: (t: TabId) => void;
  onOpen: (id: string) => void;
}

type Segment = { key: keyof typeof STATUS; count: number };

/** One stacked bar per measure, coloured by status; every segment has an icon + word in the legend. */
function StatusBar({ title, unit, segments }: { title: string; unit: string; segments: Segment[] }) {
  const [hover, setHover] = useState<Segment | null>(null);
  const total = segments.reduce((n, s) => n + s.count, 0);
  const shown = segments.filter((s) => s.count > 0);
  return (
    <div className="statbar">
      <div className="statbar-head">
        <span className="statbar-title">{title}</span>
        <span className="statbar-note" aria-live="polite">
          {hover
            ? `${STATUS[hover.key].label}: ${hover.count} ${unit}${hover.count === 1 ? "" : "s"} (${Math.round((hover.count / total) * 100)}%)`
            : `${total} ${unit}${total === 1 ? "" : "s"}`}
        </span>
      </div>
      <div className="statbar-track" role="img" aria-label={`${title}: ${shown.map((s) => `${STATUS[s.key].label} ${s.count}`).join(", ")}`}>
        {total === 0 && <span className="statbar-empty" />}
        {shown.map((s) => (
          <span key={s.key} className={`statbar-seg tone-${STATUS[s.key].tone}${hover && hover.key !== s.key ? " dim" : ""}`}
            style={{ flexGrow: s.count }} onMouseEnter={() => setHover(s)} onMouseLeave={() => setHover(null)} />
        ))}
      </div>
      <ul className="legend">
        {segments.map((s) => (
          <li key={s.key} className={`legend-item tone-${STATUS[s.key].tone}`} onMouseEnter={() => s.count && setHover(s)} onMouseLeave={() => setHover(null)}>
            <Icon name={STATUS[s.key].icon} size={14} />
            <span className="legend-label">{STATUS[s.key].label}</span>
            <b>{s.count}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string | number; sub: string }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      <span className="kpi-sub">{sub}</span>
    </div>
  );
}

export function CheckList({ rows, onOpen }: { rows: CheckRow[]; onOpen: (id: string) => void }) {
  return (
    <ul className="checklist">
      {rows.map((r) => (
        <li key={r.id}>
          <button className="check-row" onClick={() => onOpen(r.id)} disabled={!r.reopen} title={r.reopen ? "Open this check" : "Result not saved for this older check"}>
            <span className="check-kind"><Icon name={r.kind === "tender" ? "file" : "search"} size={16} /></span>
            <span className="check-main">
              <span className="check-title">{r.title}</span>
              <span className="check-meta">
                {timeAgo(r.time)} · {r.kind === "tender" ? `${r.items ?? 0} items` : "search"}
                {r.standards.length > 0 && ` · ${r.standards.slice(0, 3).join(", ")}`}
              </span>
            </span>
            {r.status && <StatusPill status={r.status} label={r.status_label} size="sm" />}
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function Dashboard({ onNavigate, onOpen }: Props) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  const load = () => api.stats().then(setStats).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const seed = async () => {
    setSeeding(true);
    try {
      await api.seedDemo();
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSeeding(false);
    }
  };

  const s = stats;
  const issues = s ? s.findings.high + s.findings.medium : 0;
  const decided = s ? s.feedback.accept + s.feedback.reject : 0;
  const maxGap = s?.top_gaps[0]?.count ?? 1;

  return (
    <div className="stack">
      <section className="hero">
        <div>
          <h2>Is this tender ready to publish?</h2>
          <p>Upload a tender or describe a product. The engine finds the Indian Standards that apply, shows where they appear in the document, and flags what is missing or outdated.</p>
        </div>
        <div className="hero-actions">
          <button className="btn btn-primary btn-lg" onClick={() => onNavigate("tender")}><Icon name="tender" /> Check a tender</button>
          <button className="btn btn-secondary btn-lg" onClick={() => onNavigate("recommend")}><Icon name="search" /> Find a standard</button>
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}
      {!s && !error && <p className="muted">Loading dashboard…</p>}

      {s && s.checks.total === 0 && (
        <section className="card empty">
          <Icon name="dashboard" size={28} />
          <h3>No compliance checks yet</h3>
          <p className="muted">Run the bundled sample tenders and example searches to fill the dashboard with real results.</p>
          <button className="btn btn-primary" onClick={seed} disabled={seeding}>{seeding ? "Running samples…" : "Load demo checks"}</button>
        </section>
      )}

      {s && s.checks.total > 0 && (
        <>
          <section className="kpis">
            <Kpi label="Compliance checks" value={s.checks.total} sub={`${s.checks.tenders} tenders · ${s.checks.searches} searches`} />
            <Kpi label="Tender items checked" value={s.items.total} sub={`${s.items.by_status.acceptable} fully compliant`} />
            <Kpi label="Issues found" value={issues} sub={`${s.findings.high} missing or outdated · ${s.findings.medium} incomplete`} />
            <Kpi label="Officer decisions" value={decided ? `${Math.round((s.feedback.accept / decided) * 100)}%` : "–"}
              sub={decided ? `accepted (${s.feedback.accept} of ${decided})` : "no accept / reject yet"} />
          </section>

          <div className="grid-2">
            <section className="card">
              <h3 className="card-title">Compliance results</h3>
              <StatusBar title="Tenders" unit="tender" segments={[
                { key: "acceptable", count: s.tenders_by_status.acceptable },
                { key: "partially_acceptable", count: s.tenders_by_status.partially_acceptable },
                { key: "not_acceptable", count: s.tenders_by_status.not_acceptable },
                { key: "not_applicable", count: s.tenders_by_status.not_applicable },
                { key: "unreadable", count: s.tenders_by_status.unreadable },
              ]} />
              <StatusBar title="Tender items" unit="item" segments={[
                { key: "acceptable", count: s.items.by_status.acceptable },
                { key: "needs_revision", count: s.items.by_status.needs_revision },
                { key: "not_acceptable", count: s.items.by_status.not_acceptable },
                { key: "not_applicable", count: s.items.by_status.not_applicable },
              ]} />
            </section>

            <section className="card">
              <h3 className="card-title">Most often missing or outdated</h3>
              {s.top_gaps.length === 0 ? (
                <p className="muted small">No missing or outdated standards found yet.</p>
              ) : (
                <ul className="rank-list">
                  {s.top_gaps.map((g) => (
                    <li key={g.label}>
                      <span className="rank-label">{g.label}</span>
                      <span className="rank-bar"><span style={{ width: `${(g.count / maxGap) * 100}%` }} /></span>
                      <b>{g.count}</b>
                    </li>
                  ))}
                </ul>
              )}
              {s.top_standards.length > 0 && (
                <p className="muted small top-std">Most matched: {s.top_standards.slice(0, 3).map((t) => t.label).join(" · ")}</p>
              )}
            </section>
          </div>

          <section className="card">
            <div className="card-head">
              <h3 className="card-title">Recent checks</h3>
              <button className="link-btn" onClick={() => onNavigate("history")}>All past checks <Icon name="arrow" size={14} /></button>
            </div>
            <CheckList rows={s.recent} onOpen={onOpen} />
          </section>
        </>
      )}
    </div>
  );
}
