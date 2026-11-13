export default function ReportBar({ reports, selected, onSelect, onRefresh, loading, report }) {
  return (
    <div className="report-bar">
      <div className="muted small">
        {report?.evaluation_date
          ? `Last run: ${new Date(report.evaluation_date).toLocaleString()}`
          : "No run recorded"}
      </div>
      <div className="report-bar-actions">
        {reports.length > 1 && (
          <select value={selected} onChange={(e) => onSelect(e.target.value)} disabled={loading} aria-label="Report">
            {reports.map((r) => (
              <option key={r.report_name} value={r.report_name}>
                {r.report_name.replace(".json", "")}
              </option>
            ))}
          </select>
        )}
        <button className="btn btn-outline" onClick={onRefresh} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>
    </div>
  );
}