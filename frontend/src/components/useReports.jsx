import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

// Loads the list of evaluation reports of one kind ("agent" | "rag") and the selected one.
export default function useReports(kind) {
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const open = useCallback(async (name) => {
    setLoading(true);
    setError("");
    try {
      const data = await api(`/api/evaluation/reports/${encodeURIComponent(name)}`);
      setReport(data.report);
      setSelected(name);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api("/api/evaluation/reports");
      const list = (data.reports || []).filter((r) => r.report_kind === kind);
      setReports(list);
      if (list.length) await open(list[0].report_name);
      else {
        setReport(null);
        setLoading(false);
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, [kind, open]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { reports, selected, report, loading, error, open, refresh };
}