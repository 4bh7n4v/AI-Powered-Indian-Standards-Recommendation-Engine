import { useEffect, useRef, useState } from "react";
import { ACCEPTED_FILES, api } from "../api";
import { markEvidence } from "../highlight";
import { GAP_KINDS, SEVERITY, STATUS, StatusPill } from "../status";
import type { TenderItem, TenderResponse } from "../types";
import CopyButton from "./CopyButton";
import Icon from "./Icon";
import MatchMeter from "./MatchMeter";

const SAMPLES = [
  { file: "01_office_complex_construction.pdf", label: "Office Complex – Administrative Block (PDF)" },
  { file: "02_district_hospital_electrification.docx", label: "District Hospital – Electrification & Water Supply (Word)" },
  { file: "03_engineering_college_hostel.pdf", label: "Engineering College – Boys Hostel (PDF)" },
  { file: "04_regional_office_facility_services.pdf", label: "Regional Office – Facility Management Services (PDF)" },
  { file: "05_government_school_building.docx", label: "सरकारी विद्यालय भवन – Government School Building (Word)" },
  { file: "06_engineering_college_hostel_scanned.pdf", label: "Engineering College – Boys Hostel, scanned copy (PDF)" },
  { file: "07_district_hospital_presentation.pptx", label: "District Hospital – as a slide deck (PowerPoint)" },
];

const STATUS_NOTE: Record<TenderResponse["summary"]["status"], string> = {
  acceptable: "Every item cites the current edition of the applicable standards, with test methods and certification.",
  partially_acceptable: "Some items are complete; others need revision before the tender is published.",
  not_acceptable: "No item is complete. Revise the specification before publishing the tender.",
  not_applicable: "No Indian Standard applies to these items (for example, services). No standards clause is needed.",
  unreadable: "The document has no readable text. It appears to be scanned; OCR is required.",
};

const TYPE_LABEL: Record<string, string> = { pdf: "PDF", docx: "Word", pptx: "PowerPoint", txt: "Text", html: "Web page", htm: "Web page" };

function Evidence({ item, docType }: { item: TenderItem; docType: string }) {
  const flagged = new Set(item.findings.map((f) => f.citation ?? "").filter(Boolean));
  if (item.evidence) {
    return (
      <figure className="evidence">
        <a href={item.evidence.image} target="_blank" rel="noreferrer" title="Open full size">
          <img src={item.evidence.image} alt={`Item ${item.index} as it appears on page ${item.evidence.page} of the uploaded document`} loading="lazy" />
        </a>
        <figcaption>
          <Icon name="image" size={14} /> Page {item.evidence.page} of the uploaded PDF
          <span className="key"><i className="k-ok" /> cited correctly <i className="k-bad" /> needs attention <i className="k-term" /> matched words</span>
        </figcaption>
      </figure>
    );
  }
  return (
    <figure className="evidence">
      <blockquote className="excerpt">{markEvidence(item.text, item.matched_terms ?? [], flagged)}</blockquote>
      <figcaption>
        <Icon name="file" size={14} /> Text from the {TYPE_LABEL[docType] ?? docType} document
        {docType === "pdf" && " (could not locate it on the page)"}
        <span className="key"><i className="k-ok" /> cited correctly <i className="k-bad" /> needs attention <i className="k-term" /> matched words</span>
      </figcaption>
    </figure>
  );
}

function ItemCard({ item, docType, open, onToggle }: { item: TenderItem; docType: string; open: boolean; onToggle: () => void }) {
  const meta = STATUS[item.status];
  return (
    <article className={`item tone-edge-${meta.tone}${open ? " open" : ""}`}>
      <button className="item-head" onClick={onToggle} aria-expanded={open}>
        <span className={`item-icon tone-${meta.tone}`}><Icon name={meta.icon} size={20} /></span>
        <span className="item-main">
          <span className="item-no">Item {item.index}</span>
          <span className="item-title">{item.title}</span>
        </span>
        <span className="item-side">
          {item.primary_standard ? <span className="tag">{item.primary_standard.label}</span> : <span className="tag tag-muted">No applicable IS</span>}
          {!item.abstained && item.primary_standard && <MatchMeter confidence={item.confidence} compact />}
          <StatusPill status={item.status} label={item.status_label} size="sm" />
          <Icon name="chevron" className="chev" />
        </span>
      </button>
      {open && (
        <div className="item-body">
          <Evidence item={item} docType={docType} />
          <div className="findings">
            {item.findings.length === 0 ? (
              <p className="ok-line">
                <Icon name={item.abstained ? "minus" : "check"} size={16} />
                {item.abstained ? "No Indian Standard applies with enough confidence (for example, a service)." : "No issues found. This item is ready."}
              </p>
            ) : (
              <ul className="finding-list">
                {item.findings.map((f, i) => {
                  const sev = SEVERITY[f.severity];
                  const gap = GAP_KINDS.has(f.kind);
                  return (
                    <li key={i} className={`finding tone-edge-${sev.tone}`}>
                      <div className="finding-top">
                        <span className={`pill pill-sm tone-${sev.tone}`}><Icon name={sev.icon} size={13} />{sev.label}</span>
                        {gap && <span className="gap-tag">Expected, not found</span>}
                      </div>
                      <p className="finding-msg">{f.message}</p>
                      {f.fix && (
                        <div className="finding-fix">
                          <span><b>Fix:</b> {f.fix}</span>
                          <CopyButton text={f.fix} label="Copy fix" />
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
            {item.suggested_clause && item.findings.length > 0 && (
              <div className="clause-box">
                <div className="clause-head"><h4>Suggested tender clause</h4><CopyButton text={item.suggested_clause} /></div>
                <blockquote className="clause">{item.suggested_clause}</blockquote>
              </div>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

interface Props {
  lang: "en" | "hi";
  autoSample?: string;
  initial?: TenderResponse;
  onResult?: (d: TenderResponse) => void;
}

export default function TenderPanel({ lang, autoSample = "", initial, onResult }: Props) {
  const [data, setData] = useState<TenderResponse | null>(initial ?? null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [link, setLink] = useState("");
  const [dragging, setDragging] = useState(false);
  const [open, setOpen] = useState<Set<number>>(() => defaultOpen(initial));
  const input = useRef<HTMLInputElement>(null);

  function defaultOpen(d?: TenderResponse | null) {
    const first = d?.items.find((i) => i.findings.length > 0) ?? d?.items[0];
    return new Set(first ? [first.index] : []);
  }

  const run = async (what: string, call: () => Promise<TenderResponse>) => {
    setBusy(what);
    setError(null);
    try {
      const d = await call();
      setData(d);
      setOpen(defaultOpen(d));
      onResult?.(d);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const analyse = (file: File) => run(`Reading ${file.name}…`, () => api.analyseTender(file, lang));
  const analyseLink = (url = link) => url.trim() && run("Downloading and reading the link…", () => api.analyseUrl(url.trim(), lang));

  const loadSample = async (file = SAMPLES[0].file) => {
    const res = await fetch(`/samples/${file}`);
    const blob = await res.blob();
    analyse(new File([blob], file, { type: blob.type }));
  };

  useEffect(() => {
    if (autoSample && !initial) loadSample(SAMPLES.find((x) => x.file.startsWith(autoSample))?.file);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = (i: number) => setOpen((s) => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n; });
  const sum = data?.summary;
  const relevant = sum ? sum.items - sum.items_by_status.not_applicable : 0;
  const tone = sum ? STATUS[sum.status].tone : "neutral";

  return (
    <div className="stack">
      <section className="card">
        <h2>Check a tender</h2>
        <p className="muted">Each item is checked for missing standards, outdated editions, missing test-method or safety standards, and certification the tender does not ask for.</p>
        <div className="intake">
          <div
            className={dragging ? "dropzone dragging" : "dropzone"}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) analyse(f); }}
          >
            <Icon name="upload" size={26} />
            <p><b>Drop a tender here</b> or</p>
            <button className="btn btn-primary" onClick={() => input.current?.click()} disabled={!!busy}>Choose file</button>
            <p className="muted small">PDF · Word · PowerPoint · Text · Web page (HTML), up to 10 MB</p>
            <input ref={input} type="file" accept={ACCEPTED_FILES} hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) analyse(f); e.target.value = ""; }} />
          </div>
          <div className="intake-side">
            <form className="link-form" onSubmit={(e) => { e.preventDefault(); analyseLink(); }}>
              <label htmlFor="tender-link"><Icon name="link" size={15} /> Or check a link</label>
              <div className="input-row">
                <input id="tender-link" type="url" placeholder="https://…/tender.pdf" value={link} onChange={(e) => setLink(e.target.value)} />
                <button className="btn btn-secondary" disabled={!!busy || !link.trim()}>Check</button>
              </div>
              <button type="button" className="link-btn small" onClick={() => {
                const u = `${window.location.origin}/samples/03_engineering_college_hostel.pdf`;
                setLink(u);
                analyseLink(u);
              }}>Try a sample link</button>
            </form>
            <label className="sample-label">
              <span><Icon name="file" size={15} /> Or use a sample tender</span>
              <select className="sample-select" value="" disabled={!!busy} onChange={(e) => e.target.value && loadSample(e.target.value)}>
                <option value="">Choose a sample…</option>
                {SAMPLES.map((x) => <option key={x.file} value={x.file}>{x.label}</option>)}
              </select>
            </label>
          </div>
        </div>
        {busy && <p className="busy"><span className="spinner" /> {busy}</p>}
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      {data && sum && (
        <>
          <section className={`verdict tone-${tone}`}>
            <span className="verdict-icon"><Icon name={STATUS[sum.status].icon} size={34} /></span>
            <div className="verdict-main">
              <span className="verdict-kicker">Overall result</span>
              <strong className="verdict-title">{sum.status_label}</strong>
              {relevant > 0 && <span className="verdict-count">{sum.items_by_status.acceptable} of {relevant} items compliant</span>}
              <p>{STATUS_NOTE[sum.status]}</p>
            </div>
            <div className="verdict-doc">
              <span><Icon name={data.document.type === "pptx" ? "slides" : "file"} size={14} /> {data.document.name}</span>
              <span className="muted small">
                {TYPE_LABEL[data.document.type] ?? data.document.type} · {data.document.pages} {data.document.type === "pptx" ? "slide" : "page"}(s)
                {data.document.source === "link" && " · from a link"} · data as of {data.data_as_of}
              </span>
              <span className="muted small" title={data.document.sha256}>SHA-256 {data.document.sha256.slice(0, 12)}…</span>
            </div>
          </section>

          {sum.items > 0 && (
            <section className="tiles">
              <div className="tile"><span className="tile-value">{sum.items}</span><span className="tile-label">Items found</span></div>
              <div className="tile tone-edge-bad"><span className="tile-value">{sum.findings.high}</span><span className="tile-label">Missing / outdated</span></div>
              <div className="tile tone-edge-warn"><span className="tile-value">{sum.findings.medium}</span><span className="tile-label">Incomplete</span></div>
              <div className="tile tone-edge-neutral"><span className="tile-value">{sum.items_without_standard}</span><span className="tile-label">No applicable IS</span></div>
            </section>
          )}

          {data.document.warnings.map((w) => <div key={w} className="alert alert-info"><Icon name="info" size={16} /> {w}</div>)}

          {data.items.length > 0 && (
            <div className="list-head">
              <h3>Items ({data.items.length})</h3>
              <div className="actions">
                <button className="link-btn" onClick={() => setOpen(new Set(data.items.map((i) => i.index)))}>Expand all</button>
                <button className="link-btn" onClick={() => setOpen(new Set())}>Collapse all</button>
              </div>
            </div>
          )}
          <div className="stack-sm">
            {data.items.map((it) => (
              <ItemCard key={it.index} item={it} docType={data.document.type} open={open.has(it.index)} onToggle={() => toggle(it.index)} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
