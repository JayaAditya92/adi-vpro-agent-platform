import { useEffect, useState } from "react";
import { api } from "../api";

export default function Content() {
  const [docs, setDocs] = useState([]);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [processing, setProcessing] = useState(null);
  const [note, setNote] = useState(null);

  async function load() {
    try {
      setDocs(await api("/api/documents"));
    } catch (err) {
      setNote({ type: "error", text: err.message });
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function upload() {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    setNote(null);
    try {
      const data = await api("/api/documents/upload", { method: "POST", body });
      setFile(null);
      await load();
      // Make the document searchable right away so the chatbot can use it.
      const list = await api("/api/documents");
      const doc = list.find((d) => d.filename === data.filename);
      if (doc && !doc.chunks) {
        setNote({ type: "ok", text: `${data.filename} uploaded. Preparing it for the AI…` });
        await prepare(doc.id);
      } else {
        setNote({ type: "ok", text: `${data.filename} is already in the library and ready.` });
      }
    } catch (err) {
      setNote({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function prepare(id) {
    setProcessing(id);
    setNote(null);
    try {
      const data = await api(`/api/documents/${id}/process`, { method: "POST" });
      setNote({ type: "ok", text: `${data.filename} is ready. The chatbot can now answer from it.` });
      await load();
    } catch (err) {
      setNote({ type: "error", text: err.message });
    } finally {
      setProcessing(null);
    }
  }

  return (
    <div className="cards-2 content-grid">
      <div className="card">
        <h3 className="h4">Add a document</h3>
        <p className="muted small">PDF, DOCX or TXT. It is prepared for the AI automatically after upload.</p>
        <label className="drop">
          <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files[0] || null)} />
          <strong>{file ? file.name : "Choose a file"}</strong>
          <span>{file ? "Ready to upload" : "Click to browse"}</span>
        </label>
        <button className="btn btn-primary btn-block" onClick={upload} disabled={!file || busy}>
          {busy ? "Uploading…" : "Upload"}
        </button>
        {note && <div className={`alert ${note.type === "ok" ? "alert-ok" : "alert-error"}`}>{note.text}</div>}
      </div>

      <div className="card">
        <h3 className="h4">Documents ({docs.length})</h3>
        {docs.length === 0 && <p className="muted small">Nothing uploaded yet.</p>}
        <div className="list">
          {docs.map((d) => (
            <div className="list-row" key={d.id}>
              <div>
                <strong>{d.filename}</strong>
                <small>{d.chunks ? `Ready for AI · ${d.chunks} sections` : "Not prepared yet — the chatbot cannot use it"}</small>
              </div>
              <button className="btn btn-outline" onClick={() => prepare(d.id)} disabled={processing !== null}>
                {processing === d.id ? "Preparing…" : d.chunks ? "Re-prepare" : "Prepare for AI"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}