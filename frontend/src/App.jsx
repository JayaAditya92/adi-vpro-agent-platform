import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";

function App() {
  const [file, setFile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

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

      setMessage(
        `${data.filename} uploaded successfully. ${data.characters_extracted} characters extracted.`
      );

      setFile(null);
      document.getElementById("documentFile").value = "";

      await loadDocuments();

    } catch (error) {
      setMessage(error.message);

    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">

      <h1>VPRO AI Agent Platform</h1>

      <p>Document Upload and Management</p>

      <div className="upload-card">

        <h2>Upload Your Knowledge Documents</h2>

        <input
          id="documentFile"
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />

        {file && (
          <p>Selected: {file.name}</p>
        )}

        <button
          onClick={uploadDocument}
          disabled={loading}
        >
          {loading ? "Uploading..." : "Upload Document"}
        </button>

        {message && (
          <p className="message">{message}</p>
        )}

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
              </tr>
            </thead>

            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.id}</td>
                  <td>{doc.filename}</td>
                  <td>{doc.characters}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

      </div>

      <p className="footer">
        React + FastAPI + PostgreSQL
      </p>

    </div>
  );
}

export default App;