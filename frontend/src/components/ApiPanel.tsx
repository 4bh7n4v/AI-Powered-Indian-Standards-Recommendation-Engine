const ENDPOINTS = [
  ["POST", "/api/recommend", "Recommend standards for a product description or specification (JSON)."],
  ["POST", "/api/tender/analyse", "Upload a tender (PDF / DOCX / PPTX / TXT / HTML) and receive a health check per item, with page snapshots for PDFs."],
  ["POST", "/api/tender/analyse-url", "Same health check for a tender at a link (PDF, Word, PowerPoint or web page)."],
  ["GET", "/api/stats", "Dashboard numbers: checks run, verdicts, issues, officer decisions."],
  ["GET", "/api/history", "Past compliance checks, newest first; /api/history/{id} returns the full saved result."],
  ["GET", "/api/standards", "List standards in the registry, filterable by domain and type."],
  ["GET", "/api/standards/{id}", "Details, current edition and certification for one standard."],
  ["GET", "/api/standards/{id}/allied", "Allied standards grouped by type."],
  ["POST", "/api/feedback", "Record an official's accept / reject decision in the audit log."],
];

const EXAMPLE = `curl -X POST http://localhost:8000/api/recommend \\
  -H "Content-Type: application/json" \\
  -d '{"query": "LED street light 90 W IP66", "top_k": 3}'`;

export default function ApiPanel() {
  return (
    <div className="stack">
      <section className="card">
        <h2>Portal Integration</h2>
        <p className="muted">
          Procurement portals integrate through a documented REST API (OpenAPI 3). The full interactive specification is
          available at <a href="/docs" target="_blank" rel="noreferrer">/docs</a>.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Method</th><th>Endpoint</th><th>Purpose</th></tr></thead>
            <tbody>
              {ENDPOINTS.map(([m, p, d]) => (
                <tr key={p + m}>
                  <td><span className={`method method-${m.toLowerCase()}`}>{m}</span></td>
                  <td className="nowrap"><code>{p}</code></td>
                  <td>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card">
        <h3>Example request</h3>
        <pre className="code">{EXAMPLE}</pre>
      </section>
    </div>
  );
}
