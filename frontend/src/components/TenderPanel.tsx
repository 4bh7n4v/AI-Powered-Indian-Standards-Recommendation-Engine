import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Finding, TenderResponse } from "../types";
import CopyButton from "./CopyButton";

const SAMPLES = [
  { file: "01_office_complex_construction.pdf", label: "Office Complex – Administrative Block" },
  { file: "02_district_hospital_electrification.docx", label: "District Hospital – Electrification & Water Supply" },
  { file: "03_engineering_college_hostel.pdf", label: "Engineering College – Boys Hostel" },
  { file: "04_regional_office_facility_services.pdf", label: "Regional Office – Facility Management Services" },
  { file: "05_government_school_building.docx", label: "सरकारी विद्यालय भवन (Government School Building)" },
  { file: "06_engineering_college_hostel_scanned.pdf", label: "Engineering College – Boys Hostel (scanned copy)" },
];

const STATUS_NOTE: Record<TenderResponse["summary"]["status"], string> = {
  acceptable: "Every item cites the current edition of the applicable standards, with test methods and certification.",
  partially_acceptable: "Some items are complete; others need revision before the tender is published.",
  not_acceptable: "No item is complete. Revise the specification before publishing the tender.",
  not_applicable: "No Indian Standard applies to these items (for example, services). No standards clause is needed.",
  unreadable: "The document has no readable text. It appears to be scanned; OCR is required.",
};

const SEVERITY: Record<Finding["severity"], string> = {
  high: "Missing / outdated",
  medium: "Incomplete",
  low: "Minor",
  info: "Check manually",
};

export default function TenderPanel({ lang, autoSample = "" }: { lang: "en" | "hi"; autoSample?: string }) {
  const [data, setData] = useState<TenderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const analyse = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      setData(await api.analyseTender(file, lang));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loadSample = async (file = SAMPLES[0].file) => {
    const res = await fetch(`/samples/${file}`);
    const blob = await res.blob();
    analyse(new File([blob], file, { type: blob.type }));
  };

  useEffect(() => {
    if (autoSample) loadSample(SAMPLES.find((x) => x.file.startsWith(autoSample))?.file);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="stack">
      <section className="card">
        <h2>Tender Specification Health Check</h2>
        <p className="muted">
          Upload a tender document (PDF, DOCX or TXT, up to 10 MB). Each item is checked for missing standards, outdated
          editions, missing test-method or safety standards, and unstated certification requirements.
        </p>
        <div
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) analyse(f); }}
        >
          <p>Drag and drop a tender document here</p>
          <div className="actions center">
            <button className="btn btn-primary" onClick={() => input.current?.click()} disabled={busy}>Choose file</button>
            <select
              className="sample-select"
              value=""
              disabled={busy}
              onChange={(e) => e.target.value && loadSample(e.target.value)}
              aria-label="Use a sample tender"
            >
              <option value="">Use a sample tender…</option>
              {SAMPLES.map((x) => <option key={x.file} value={x.file}>{x.label}</option>)}
            </select>
          </div>
          <input ref={input} type="file" accept=".pdf,.docx,.txt" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) analyse(f); e.target.value = ""; }} />
        </div>
        {busy && <p className="muted">Analysing document…</p>}
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      {data && (
        <>
          <section className={`status-banner status-${data.summary.status}`}>
            <div>
              <span className="status-kicker">Overall result</span>
              <strong className="status-title">{data.summary.status_label}</strong>
              <p>{STATUS_NOTE[data.summary.status]}</p>
            </div>
            {data.summary.items > 0 && (
              <div className="status-counts">
                <span><b>{data.summary.items_by_status.acceptable}</b> acceptable</span>
                <span><b>{data.summary.items_by_status.needs_revision}</b> need revision</span>
                <span><b>{data.summary.items_by_status.not_acceptable}</b> not acceptable</span>
                <span><b>{data.summary.items_by_status.not_applicable}</b> no applicable IS</span>
              </div>
            )}
          </section>
          <section className="summary-grid">
            <div className="stat"><span className="stat-value">{data.summary.items}</span><span className="stat-label">Items found</span></div>
            <div className="stat stat-red"><span className="stat-value">{data.summary.findings.high}</span><span className="stat-label">Missing / outdated</span></div>
            <div className="stat stat-amber"><span className="stat-value">{data.summary.findings.medium}</span><span className="stat-label">Incomplete</span></div>
            <div className="stat"><span className="stat-value">{data.summary.items_without_standard}</span><span className="stat-label">No applicable IS</span></div>
          </section>
          <p className="muted small">
            {data.document.name} · {data.document.type.toUpperCase()} · {data.document.pages} page(s) · SHA-256 {data.document.sha256.slice(0, 12)}… · data as of {data.data_as_of}
          </p>
          {data.document.warnings.map((w) => <div key={w} className="alert alert-info">{w}</div>)}

          <div className="stack">
            {data.items.map((it) => (
              <article key={it.index} className="card item">
                <div className="item-head">
                  <span className="item-no">Item {it.index}</span>
                  <span className="item-title">{it.title}</span>
                  <span className={`item-status is-${it.status}`}>{it.status_label}</span>
                  {it.primary_standard ? (
                    <span className="tag">{it.primary_standard.label}</span>
                  ) : (
                    <span className="tag tag-muted">No applicable IS</span>
                  )}
                </div>
                <p className="item-text">{it.text}</p>
                {it.findings.length === 0 ? (
                  <p className="ok-line">{it.abstained ? "No Indian Standard applies with enough confidence (for example, a service)." : "No issues found."}</p>
                ) : (
                  <table className="table findings">
                    <thead><tr><th>Severity</th><th>Finding</th><th>Suggested fix</th></tr></thead>
                    <tbody>
                      {it.findings.map((f, i) => (
                        <tr key={i}>
                          <td><span className={`sev sev-${f.severity}`}>{SEVERITY[f.severity]}</span></td>
                          <td>{f.message}</td>
                          <td>{f.fix ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {it.suggested_clause && it.findings.length > 0 && (
                  <div className="clause-row">
                    <blockquote className="clause">{it.suggested_clause}</blockquote>
                    <CopyButton text={it.suggested_clause} />
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
