import { useEffect, useMemo, useState } from "react";
import { CATEGORY_LABELS, api } from "../api";
import type { RegistryResponse } from "../types";

export default function RegistryPanel() {
  const [data, setData] = useState<RegistryResponse | null>(null);
  const [domain, setDomain] = useState("");
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.registry().then(setData).catch((e) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    const f = filter.toLowerCase();
    return data.standards.filter(
      (s) => (!domain || s.domain === domain) && (!f || s.label.toLowerCase().includes(f) || s.title.toLowerCase().includes(f)),
    );
  }, [data, domain, filter]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return <p className="muted">Loading registry…</p>;

  return (
    <section className="card">
      <h2>Standards Registry</h2>
      <p className="muted">
        {data.standards.length} standards in {Object.keys(data.meta.domains).length} product domains · as of {data.meta.as_of} ·{" "}
        {data.meta.verified ? "verified" : "not yet verified against the BIS portal"}
      </p>
      <div className="toolbar">
        <select value={domain} onChange={(e) => setDomain(e.target.value)} aria-label="Domain">
          <option value="">All domains</option>
          {Object.entries(data.meta.domains).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input type="search" placeholder="Filter by IS number or title" value={filter} onChange={(e) => setFilter(e.target.value)} />
      </div>
      <p className="muted small">Showing {rows.length} of {data.standards.length}</p>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Standard</th><th>Title</th><th>Type</th><th>Domain</th></tr></thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td className="nowrap"><span className="std-number small">{s.label}</span></td>
                <td>{s.title}</td>
                <td className="nowrap">{CATEGORY_LABELS[s.category] ?? s.category}</td>
                <td>{data.meta.domains[s.domain]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
