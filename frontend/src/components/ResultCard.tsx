import { useState } from "react";
import { ALLIED_LABELS, CATEGORY_LABELS, api } from "../api";
import { highlightTerms } from "../highlight";
import type { Recommendation } from "../types";
import CopyButton from "./CopyButton";
import Icon from "./Icon";
import MatchMeter from "./MatchMeter";

interface Props {
  rank: number;
  rec: Recommendation;
  requestId: string;
}

export default function ResultCard({ rank, rec, requestId }: Props) {
  const [open, setOpen] = useState(rank === 1);
  const [decision, setDecision] = useState<"accept" | "reject" | null>(null);
  const s = rec.standard;
  const v = rec.version;

  const decide = (d: "accept" | "reject") => api.feedback(requestId, s.id, d).then(() => setDecision(d));

  return (
    <article className={`card result${rank === 1 ? " top" : ""}`}>
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
        <MatchMeter confidence={rec.confidence} cited={rec.evidence.cited_in_input} />
      </div>

      <div className="badges">
        <span className={v.cited_is_outdated ? "badge tone-bad" : "badge tone-info"}>
          <Icon name={v.cited_is_outdated ? "cross" : "check"} size={13} />
          {v.cited_is_outdated ? `Cited edition ${v.cited_year} is outdated · current ${v.current_edition}` : `Current edition: ${v.current_edition}`}
        </span>
        <span className="badge tone-neutral" title={v.amendments_note ?? ""}>
          {v.amendments.length ? `${v.amendments.length} amendment(s)` : "Amendments: to be verified"}
        </span>
        {rec.certification.map((c) => (
          <span key={c.label} className={c.scheme ? "badge tone-warn" : "badge tone-neutral"}
            title={`${c.basis}${c.verified ? "" : " · source to be verified on the BIS portal"}`}>
            {c.scheme && <Icon name="alert" size={13} />}
            {c.scheme ? `${c.label} ${c.status === "mandatory" ? "required" : "likely required"}` : c.label}
          </span>
        ))}
      </div>

      <button className="link-btn details-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? "Hide details" : "Show details"} <Icon name="chevron" size={14} className={open ? "flip" : ""} />
      </button>

      {open && (
        <div className="result-body">
          <section>
            <h4>Why this standard?</h4>
            <p className="scope">{highlightTerms(rec.evidence.scope_text, rec.evidence.matched_terms)}</p>
            <p className="muted small">
              {rec.evidence.cited_in_input
                ? "The input cites this standard directly."
                : rec.evidence.matched_terms.length
                  ? `Matched words: ${rec.evidence.matched_terms.join(", ")}`
                  : "Matched by meaning (semantic similarity)."}
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
              <h4>Related standards to cite with it</h4>
              <div className="table-wrap">
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
              </div>
            </section>
          )}

          <section>
            <div className="clause-head"><h4>Suggested tender clause</h4><CopyButton text={rec.clause} /></div>
            <blockquote className="clause">{rec.clause}</blockquote>
            <div className="actions">
              <span className="muted small">Is this the right standard?</span>
              <span className="spacer" />
              {decision ? (
                <span className={decision === "accept" ? "decision ok" : "decision no"}>
                  <Icon name={decision === "accept" ? "check" : "cross"} size={15} />
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
