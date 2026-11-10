import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";

function App() {
  const [file, setFile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [message, setMessage] = useState("");

  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState("");

  async function loadDocuments() {
    try {
      const response = await fetch(`${API_URL}/api/documents`);

      if (!response.ok) {
        throw new Error("Unable to load documents");
      }

      const data = await response.json();
      setDocuments(data);

    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function uploadDocument() {
    if (!file) {
      setMessage("Please select a document");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API_URL}/api/documents/upload`,
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      if (data.status === "already_exists") {
        setMessage(
          `${data.filename} already exists. No duplicate record was created.`
        );
      } else {
        setMessage(
          `${data.filename} uploaded successfully. ${data.characters_extracted} characters extracted.`
        );
      }

      setFile(null);

      document.getElementById("documentFile").value = "";

      await loadDocuments();

    } catch (error) {
      setMessage(error.message);

    } finally {
      setLoading(false);
    }
  }

  async function processDocument(id) {
    setProcessingId(id);
    setMessage("");

    try {
      const response = await fetch(
        `${API_URL}/api/documents/${id}/process`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Processing failed");
      }

      setMessage(
        `${data.filename}: ${data.total_chunks} chunks created with ${data.embedding_dimensions}-dimensional embeddings.`
      );

    } catch (error) {
      setMessage(error.message);

    } finally {
      setProcessingId(null);
    }
  }

  async function searchDocuments() {
    if (!searchQuery.trim()) {
      setSearchMessage("Please enter a question");
      setSearchResults([]);
      return;
    }

    setSearching(true);
    setSearchMessage("");
    setSearchResults([]);

    try {
      const response = await fetch(
        `${API_URL}/api/search`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            query: searchQuery
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Search failed");
      }

      setSearchResults(data.results);

      if (data.total_results === 0) {
        setSearchMessage(
          "No matching document chunks found. Upload and process a document first."
        );
      } else {
        setSearchMessage(
          `${data.total_results} matching chunk(s) found.`
        );
      }

    } catch (error) {
      setSearchMessage(error.message);

    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="container">

      <header className="page-header">
        <h1>VPRO AI Agent Platform</h1>
        <p>Document Management and Semantic Search System</p>
      </header>

      {/* Document Upload */}
      <section className="card">
        <h2>Upload Knowledge Documents</h2>

        <input
          id="documentFile"
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />

        {file && (
          <p className="selected-file">
            Selected: {file.name}
          </p>
        )}

        <button
          onClick={uploadDocument}
          disabled={loading}
        >
          {loading ? "Uploading..." : "Upload Document"}
        </button>
      </section>

      {/* Uploaded Documents */}
      <section className="card">
        <h2>Uploaded Documents</h2>

        {documents.length === 0 ? (
          <p>No documents uploaded yet.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Filename</th>
                  <th>Characters</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>{doc.id}</td>
                    <td>{doc.filename}</td>
                    <td>{doc.characters}</td>
                    <td>
                      <button
                        onClick={() => processDocument(doc.id)}
                        disabled={processingId !== null}
                      >
                        {processingId === doc.id
                          ? "Processing..."
                          : "Generate Embeddings"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Upload and Processing Messages */}
      {message && (
        <div className="message-card">
          {message}
        </div>
      )}

      {/* Semantic Search */}
      <section className="card search-card">
        <h2>Semantic Document Search</h2>

        <p>
          Ask a question about your uploaded knowledge documents.
        </p>

        <textarea
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Example: What is Python and what are its main features?"
          rows={4}
        />

        <button
          onClick={searchDocuments}
          disabled={searching}
        >
          {searching ? "Searching..." : "Search Documents"}
        </button>

        {searchMessage && (
          <p className="search-message">
            {searchMessage}
          </p>
        )}

        {searchResults.length > 0 && (
          <div className="results-container">
            <h3>Top Matching Results</h3>

            {searchResults.map((result, index) => (
              <article
                className="result-card"
                key={`${result.document_id}-${result.chunk_number}`}
              >
                <div className="result-header">
                  <h4>Result {index + 1}</h4>
                  <span>{result.filename}</span>
                </div>

                <p>{result.content}</p>

                <div className="result-metrics">
                  <span>
                    Document ID: {result.document_id}
                  </span>

                  <span>
                    Chunk: {result.chunk_number}
                  </span>

                  <span>
                    Cosine Distance: {result.cosine_distance}
                  </span>

                  <span>
                    Cosine Similarity: {result.cosine_similarity}
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className="footer">
        React + FastAPI + LangChain + Amazon Bedrock + PostgreSQL + pgvector
      </footer>

    </div>
  );
}

export default App;