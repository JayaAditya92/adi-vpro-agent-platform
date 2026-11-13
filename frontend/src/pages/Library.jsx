import { useEffect, useState } from "react";
import { api } from "../api";

export default function Library() {
  const [docs, setDocs] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/documents")
      .then(setDocs)
      .catch((err) => {
        setDocs([]);
        setError(err.message);
      });
  }, []);

  async function search(event) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const data = await api("/api/search", {
        method: "POST",
        body: JSON.stringify({ query }),
      });
      setResults(data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="container page">
      <div className="page-head">
        <h1>Course library</h1>
        <p className="muted">Search your learning material and see what is available.</p>
      </div>

      <form className="search-bar" onSubmit={search}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a topic, e.g. Python lists"
        />
        <button className="btn btn-primary" disabled={searching || !query.trim()}>
          {searching ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {results && (
        <div className="block">
          <h2 className="h3">
            {results.length ? `${results.length} matching passage${results.length > 1 ? "s" : ""}` : "No matches found"}
          </h2>
          {results.map((r) => (
            <article className="card result" key={`${r.document_id}-${r.chunk_number}`}>
              <div className="result-head">
                <strong>{r.filename}</strong>
                <span className="pill">{Math.round((r.cosine_similarity ?? 0) * 100)}% match</span>
              </div>
              <p>{r.content}</p>
            </article>
          ))}
        </div>
      )}

      <div className="block">
        <h2 className="h3">Available documents {docs && <span className="count">{docs.length}</span>}</h2>
        {docs === null && <p className="muted">Loading…</p>}
        {docs?.length === 0 && !error && <p className="muted">No documents have been added yet.</p>}
        <div className="doc-grid">
          {docs?.map((d) => (
            <div className="card doc" key={d.id}>
              <span className="doc-ext">{(d.filename.split(".").pop() || "doc").toUpperCase()}</span>
              <div>
                <strong>{d.filename}</strong>
                <small>{Math.max(1, Math.round(d.characters / 1000))}k characters</small>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}