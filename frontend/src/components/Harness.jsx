import { useState } from "react";
import { toolLabel } from "../api";
import useReports from "./useReports";
import ReportBar from "./ReportBar";

const AGENT_NAMES = { tool_agent: "Tool Agent", mcp_agent: "MCP Agent" };
const CATEGORY_NAMES = {
  calculator: "Calculator",
  knowledge_search: "Knowledge search",
  security: "Security",
};

const pct = (n, d) => (d ? Math.round((n / d) * 100) : 0);
const label = (key, map) => map[key] || key;

function Group({ title, rows }) {
  return (
    <div className="card">
      <h3 className="h4">{title}</h3>
      <div className="bars">
        {rows.map((r) => (
          <div className="bar-row" key={r.name}>
            <div className="bar-label">
              <span>{r.name}</span>
              <b>
                {r.passed}/{r.total} passed
              </b>
            </div>
            <div className="bar">
              <div className={r.passed === r.total ? "ok" : "bad"} style={{ width: `${pct(r.passed, r.total)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function groupBy(results, key, names) {
  const map = {};
  for (const r of results) {
    const k = r[key] || "other";
    map[k] ??= { name: label(k, names), passed: 0, total: 0 };
    map[k].total += 1;
    if (r.evaluation?.gate_status === "PASS") map[k].passed += 1;
  }
  return Object.values(map);
}

export default function Harness() {
  const { reports, selected, report, loading, error, open, refresh } = useReports("agent");
  const [openId, setOpenId] = useState(null);

  const results = report?.results || [];

  const stats = {
    checks: results.reduce((a, r) => a + (r.evaluation?.total_checks || 0), 0),
    checksPassed: results.reduce((a, r) => a + (r.evaluation?.passed_checks || 0), 0),
  };

  const total = report?.total_test_cases ?? results.length;
  const passed = report?.passed_test_cases ?? 0;
  const rate = report?.pass_percentage ?? pct(passed, total);
  const healthy = report?.overall_status === "PASS";

  return (
    <div>
      <div className="explain">
        <b>What this shows:</b> the test harness asks the agent a fixed set of questions and checks each answer
        automatically: Did it use the right tool? Is the answer correct? Did it block unsafe requests? A test case
        passes only when all its checks pass.
      </div>

      <ReportBar reports={reports} selected={selected} onSelect={open} onRefresh={refresh} loading={loading} report={report} />
      {error && <div className="alert alert-error">{error}</div>}

      {!report && !loading && !error && (
        <div className="card empty">
          <h3 className="h4">No agent test results yet</h3>
          <p className="muted">
            Run <code>python run_live_agent_evaluation.py</code> in the backend folder, then press Refresh.
          </p>
        </div>
      )}

      {report && (
        <>
          <div className="kpis">
            <div className={`kpi kpi-hero ${healthy ? "good" : "bad"}`}>
              <span>Overall result</span>
              <strong>{healthy ? "Healthy" : "Needs attention"}</strong>
              <small>{rate}% of tests passed</small>
            </div>
            <div className="kpi">
              <span>Test cases</span>
              <strong>{total}</strong>
              <small>questions asked to the agents</small>
            </div>
            <div className="kpi">
              <span>Passed</span>
              <strong className="t-good">{passed}</strong>
              <small>all checks succeeded</small>
            </div>
            <div className="kpi">
              <span>Failed</span>
              <strong className={report.failed_test_cases ? "t-bad" : "t-good"}>{report.failed_test_cases ?? 0}</strong>
              <small>{stats.checksPassed}/{stats.checks} individual checks passed</small>
            </div>
          </div>

          <div className="cards-2">
            <Group title="By agent" rows={groupBy(results, "agent_type", AGENT_NAMES)} />
            <Group title="By skill tested" rows={groupBy(results, "category", CATEGORY_NAMES)} />
          </div>

          <h2 className="h3 block-title">Test cases</h2>
          <div className="table">
            {results.map((r) => {
              const ev = r.evaluation || {};
              const ok = ev.gate_status === "PASS";
              const isOpen = openId === r.test_id;
              const tools = (r.agent_result?.tool_calls || []).map((c) => toolLabel(c.name || c.tool));
              return (
                <div className="trow" key={r.test_id}>
                  <button className="trow-head" onClick={() => setOpenId(isOpen ? null : r.test_id)} aria-expanded={isOpen}>
                    <span className={`dot ${ok ? "ok" : "bad"}`} />
                    <span className="trow-id">{r.test_id}</span>
                    <span className="trow-q">{r.question}</span>
                    <span className="trow-tag">{label(r.agent_type, AGENT_NAMES)}</span>
                    <span className={`status ${ok ? "ok" : "bad"}`}>{ok ? "Passed" : "Failed"}</span>
                    <span className="trow-checks">{ev.passed_checks}/{ev.total_checks} checks</span>
                  </button>
                  {isOpen && (
                    <div className="trow-body">
                      <div className="kv">
                        <span>Agent's answer</span>
                        <p>{r.agent_result?.answer || "—"}</p>
                      </div>
                      <div className="kv">
                        <span>Tools used</span>
                        <p>{tools.length ? tools.join(", ") : "None"}</p>
                      </div>
                      <div className="kv">
                        <span>Security</span>
                        <p>
                          {r.agent_result?.security?.status === "blocked"
                            ? `Blocked: ${r.agent_result.security.reason || "unsafe request"}`
                            : "Passed"}
                        </p>
                      </div>
                      <div className="kv">
                        <span>Checks</span>
                        <ul className="checks">
                          {(ev.checks || []).map((c) => (
                            <li key={c.name} className={c.passed ? "ok" : "bad"}>
                              <b>{c.passed ? "✓" : "✕"}</b> {c.name.replace(/_/g, " ")}
                              {!c.passed && <em> — {c.message}</em>}
                            </li>
                          ))}
                        </ul>
                      </div>
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