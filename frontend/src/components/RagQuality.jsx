import { useState } from "react";
import useReports from "./useReports";
import ReportBar from "./ReportBar";

const METRICS = [
  { key: "faithfulness", label: "Faithfulness", help: "Answer sticks to the source documents" },
  { key: "context_precision", label: "Context precision", help: "Retrieved passages are relevant" },
  { key: "context_recall", label: "Context recall", help: "Nothing important was missed" },
  { key: "answer_relevance", label: "Answer relevance", help: "Answer addresses the question" },
  { key: "answer_correctness", label: "Answer correctness", help: "Answer matches the reference" },
];

const fmt = (v) => (typeof v === "number" ? `${Math.round(v * 100)}%` : "N/A");
const tone = (v) => (typeof v !== "number" ? "" : v >= 0.9 ? "ok" : v >= 0.7 ? "warn" : "bad");

export default function RagQuality() {
  const { reports, selected, report, loading, error, open, refresh } = useReports("rag");
  const [openIdx, setOpenIdx] = useState(null);
  const scores = report?.average_ragas_scores || {};
  const results = report?.results || [];

  return (
    <div>
      <div className="explain">
        <b>What this shows:</b> how good the AI's document-based answers are. Each score is out of 100%; 90% or
        higher is excellent, below 70% needs work.
      </div>

      <ReportBar reports={reports} selected={selected} onSelect={open} onRefresh={refresh} loading={loading} report={report} />
      {error && <div className="alert alert-error">{error}</div>}

      {!report && !loading && !error && (
        <div className="card empty">
          <h3 className="h4">No RAG evaluation results yet</h3>
          <p className="muted">Run the RAG evaluation in the backend, then press Refresh.</p>
        </div>
      )}

      {report && (
        <>
          <div className="metric-grid">
            {METRICS.map((m) => (
              <div className="card metric" key={m.key}>
                <span>{m.label}</span>
                <strong className={`t-${tone(scores[m.key])}`}>{fmt(scores[m.key])}</strong>
                <div className="bar">
                  <div className={tone(scores[m.key])} style={{ width: `${Math.min(100, (scores[m.key] || 0) * 100)}%` }} />
                </div>
                <small>{m.help}</small>
              </div>
            ))}
          </div>

          <h2 className="h3 block-title">
            Questions tested ({report.successful_records ?? results.length}/{report.total_records ?? results.length} evaluated)
          </h2>
          <div className="table">
            {results.map((r, i) => {
              const isOpen = openIdx === i;
              return (
                <div className="trow" key={i}>
                  <button className="trow-head" onClick={() => setOpenIdx(isOpen ? null : i)} aria-expanded={isOpen}>
                    <span className={`dot ${r.status === "success" ? "ok" : "bad"}`} />
                    <span className="trow-id">Q{i + 1}</span>
                    <span className="trow-q">{r.question}</span>
                    <span className={`status ${r.status === "success" ? "ok" : "bad"}`}>{r.status === "success" ? "Evaluated" : "Failed"}</span>
                  </button>
                  {isOpen && (
                    <div className="trow-body">
                      <div className="kv"><span>AI answer</span><p>{r.generated_answer || "—"}</p></div>
                      <div className="kv"><span>Reference answer</span><p>{r.reference_answer || "—"}</p></div>
                      <div className="kv">
                        <span>Scores</span>
                        <p>
                          {METRICS.map((m) => `${m.label}: ${fmt(r.ragas_metrics?.[m.key])}`).join(" · ")}
                        </p>
                      </div>
                      {r.error && <div className="alert alert-error">{r.error}</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}