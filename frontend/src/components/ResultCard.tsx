import { useState } from "react";
import { ALLIED_LABELS, CATEGORY_LABELS, api } from "../api";
import type { Recommendation } from "../types";
import CopyButton from "./CopyButton";

interface Props {
  rank: number;
  rec: Recommendation;
  requestId: string;
}

function highlight(text: string, terms: string[]) {
  if (!terms.length) return text;
  const re = new RegExp(`\\b(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\w*`, "gi");
  const parts = text.split(re);
  return parts.map((p, i) => (i % 2 === 1 ? <mark key={i}>{p}</mark> : p));
}

export default function ResultCard({ rank, rec, requestId }: Props) {
  const [open, setOpen] = useState(rank === 1);
  const [decision, setDecision] = useState<"accept" | "reject" | null>(null);
  const s = rec.standard;
  const v = rec.version;
  const pct = Math.round(rec.confidence * 100);

  const decide = (d: "accept" | "reject") => api.feedback(requestId, s.id, d).then(() => setDecision(d));

  return (
    <article className="card result">
      <div className="result-head">
        <div className="rank">{rank}</div>
        <div className="result-title">
          <div className="std-line">
            <span className="std-number">{s.label}</span>
            <span className="tag">{CATEGORY_LABELS[s.category] ?? s.category}</span>
            <span className="tag tag-muted">{s.domain_name}</span>
          </div>
          <h3>{s.title}</h3>
        </div>
        <div className="confidence" title="Match confidence">
          <div className="bar"><span style={{ width: `${pct}%` }} /></div>
          <small>{rec.evidence.cited_in_input ? "Cited in input" : `${pct}% match`}</small>
        </div>
      </div>

      <div className="badges">
        <span className={v.cited_is_outdated ? "badge badge-red" : "badge badge-blue"}>
          {v.cited_is_outdated ? `Cited edition ${v.cited_year} is outdated · current ${v.current_edition}` : `Current edition: ${v.current_edition}`}
        </span>
        <span className="badge badge-grey">
          {v.amendments.length ? `${v.amendments.length} amendment(s)` : "Amendments: to be verified"}
        </span>
        {rec.certification.map((c) => (
          <span key={c.label} className={c.scheme ? "badge badge-amber" : "badge badge-grey"} title={c.basis}>
            {c.scheme ? `${c.label}${c.verified ? "" : " · to verify"}` : c.label}
          </span>
        ))}
      </div>

      <button className="link-btn" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? "Hide details" : "Show details"}
      </button>

      {open && (
        <div className="result-body">
          <section>
            <h4>Why this standard?</h4>
            <p className="scope">{highlight(rec.evidence.scope_text, rec.evidence.matched_terms)}</p>
            <p className="muted small">
              {rec.evidence.cited_in_input
                ? "The input cites this standard directly."
                : rec.evidence.matched_terms.length
                  ? `Matched terms: ${rec.evidence.matched_terms.join(", ")}`
                  : "Matched by semantic similarity."}
              {rec.evidence.dense_similarity !== null && ` · semantic similarity ${rec.evidence.dense_similarity}`}
            </p>
          </section>

          {rec.certification.some((c) => c.scheme) && (
            <section>
              <h4>Certification</h4>
              <ul className="plain">
                {rec.certification.filter((c) => c.scheme).map((c) => (
                  <li key={c.label}>
                    <strong>{c.name}</strong> — {c.basis}
                    {c.effective_from && `, effective ${c.effective_from}`}. {!c.verified && <em className="muted">Source to be verified.</em>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {Object.keys(rec.allied).length > 0 && (
            <section>
              <h4>Allied standards</h4>
              <table className="table compact">
                <tbody>
                  {Object.entries(rec.allied).map(([type, list]) => (
                    <tr key={type}>
                      <th>{ALLIED_LABELS[type] ?? type}</th>
                      <td>
                        {list.map((a) => (
                          <div key={a.id}>
                            <span className="std-number small">{a.label}</span> <span className="muted">{a.title}</span>
                          </div>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section>
            <h4>Suggested tender clause</h4>
            <blockquote className="clause">{rec.clause}</blockquote>
            <div className="actions">
              <CopyButton text={rec.clause} />
              <span className="spacer" />
              {decision ? (
                <span className={decision === "accept" ? "decision ok" : "decision no"}>
                  {decision === "accept" ? "Accepted" : "Rejected"} · recorded in audit log
                </span>
              ) : (
                <>
                  <button className="btn btn-primary btn-sm" onClick={() => decide("accept")}>Accept</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => decide("reject")}>Reject</button>
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </article>
  );
}
