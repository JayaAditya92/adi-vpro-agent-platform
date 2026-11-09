
import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";

function App() {
  const [file, setFile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);

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

      // setMessage(
      //   `${data.filename} uploaded successfully. ${data.characters_extracted} characters extracted.`
      // );
      if (data.status === "already_exists") {
        setMessage(
          `${data.filename} already exists. No duplicate record was created. ${data.characters_extracted} characters checked.`
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

  return (
    <div className="container">

      <h1>VPRO AI Agent Platform</h1>

      <p>Document Chunking and Embedding System</p>

      <div className="upload-card">

        <h2>Upload Knowledge Documents</h2>

        <input
          id="documentFile"
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />

        {file && <p>Selected: {file.name}</p>}

        <button
          onClick={uploadDocument}
          disabled={loading}
        >
          {loading ? "Uploading..." : "Upload Document"}
        </button>

      </div>

      <div className="documents-card">

        <h2>Uploaded Documents</h2>

        {documents.length === 0 ? (
          <p>No documents uploaded yet.</p>
        ) : (
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
        )}

      </div>

      {message && (
        <div className="message-card">
          {message}
        </div>
      )}

      <p className="footer">
        React + FastAPI + LangChain + Bedrock + PostgreSQL
      </p>

    </div>
  );
}

export default App;