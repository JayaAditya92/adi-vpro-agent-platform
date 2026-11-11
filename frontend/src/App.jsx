import { useEffect, useState } from "react";
import "./MCPAgent.css";

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

  const [chatSessions, setChatSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);

  // Lesson 10: MCP-powered Agent state
  const [mcpQuestion, setMcpQuestion] = useState("");
  const [mcpMessages, setMcpMessages] = useState([]);
  const [mcpLoading, setMcpLoading] = useState(false);
  const [mcpError, setMcpError] = useState("");

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
    loadChatSessions();
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

  async function loadChatSessions() {
    try {
      const response = await fetch(`${API_URL}/api/chat/sessions`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Unable to load chat sessions");
      }

      const data = await response.json();
      setChatSessions(Array.isArray(data) ? data : []);
    } catch (error) {
      setSearchMessage(error.message);
      setChatSessions([]);
    }
  }

async function createChatSession() {
  if (creatingSession) return;

  setCreatingSession(true);
  setSearchMessage("");

  try {
    const response = await fetch(`${API_URL}/api/chat/sessions`, {
      method: "POST"
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Unable to create chat session");
    }

    // The FastAPI endpoint returns the primary key as "id".
    if (!Number.isInteger(data.id)) {
      throw new Error("The server did not return a valid chat session ID.");
    }

    setActiveSessionId(data.id);
    setChatMessages([]);
    await loadChatSessions();
  } catch (error) {
    setSearchMessage(error.message);
  } finally {
    setCreatingSession(false);
  }
}

async function openChatSession(sessionId) {
  const validSessionId = Number(sessionId);

  if (!Number.isInteger(validSessionId) || validSessionId <= 0) {
    setSearchMessage("Invalid conversation ID. Please create a new conversation.");
    return;
  }

  try {
    const response = await fetch(
      `${API_URL}/api/chat/sessions/${validSessionId}/messages`
    );

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Unable to load conversation");
    }

    setActiveSessionId(validSessionId);
    setChatMessages(Array.isArray(data) ? data : []);
    setSearchMessage("");
  } catch (error) {
    setSearchMessage(error.message);
  }
}

async function sendChatMessage() {
  if (!chatQuestion.trim() || !Number.isInteger(Number(activeSessionId)) || Number(activeSessionId) <= 0) {
    return;
  }

  const question = chatQuestion.trim();

  setChatQuestion("");
  setChatLoading(true);

  setChatMessages((previous) => [
    ...previous,
    {
      role: "user",
      content: question
    }
  ]);

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        session_id: Number(activeSessionId),
        question
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Chat request failed");
    }

    setChatMessages((previous) => [
      ...previous,
      {
        role: "assistant",
        content: data.answer
      }
    ]);

    await loadChatSessions();

  } catch (error) {
    setChatMessages((previous) => [
      ...previous,
      {
        role: "assistant",
        content: `Error: ${error.message}`
      }
    ]);

  } finally {
    setChatLoading(false);
  }
}

  async function sendMCPMessage(event) {
    event.preventDefault();
    const question = mcpQuestion.trim();
    if (!question || mcpLoading) return;

    setMcpQuestion("");
    setMcpError("");
    setMcpMessages((previous) => [...previous, { role: "user", content: question }]);
    setMcpLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/mcp-agent/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "MCP Agent request failed");

      setMcpMessages((previous) => [...previous, {
        role: "assistant",
        content: data.answer || "The agent returned an empty answer.",
        toolCalls: Array.isArray(data.tool_calls) ? data.tool_calls : []
      }]);
    } catch (error) {
      setMcpError(error.message || "Unable to contact the MCP Agent.");
    } finally {
      setMcpLoading(false);
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

      {/* Lesson 10: MCP-powered Agent */}
      <section className="card mcp-agent-card">
        <div className="mcp-agent-heading">
          <div>
            <h2>VPRO MCP Agent</h2>
            <p>LangGraph + Amazon Bedrock + MCP Tools</p>
          </div>
          <span className="mcp-agent-status">MCP Agent</span>
        </div>

        <div className="mcp-agent-messages">
          {mcpMessages.length === 0 && (
            <div className="mcp-agent-welcome">
              <h3>Ask the VPRO AI Agent</h3>
              <p>Ask a question, perform a calculation, or search your uploaded course documents.</p>
              <div className="mcp-agent-examples">
                <button type="button" onClick={() => setMcpQuestion("Calculate 250 multiplied by 4 plus 150.")}>Test calculator</button>
                <button type="button" onClick={() => setMcpQuestion("What are the main features of Python? Use my uploaded knowledge documents.")}>Search Python knowledge</button>
              </div>
            </div>
          )}

          {mcpMessages.map((item, index) => (
            <div key={`mcp-${index}`} className={`mcp-agent-message ${item.role}`}>
              <strong>{item.role === "user" ? "You" : "VPRO AI Agent"}</strong>
              <div className="mcp-agent-message-content">{item.content}</div>
              {item.toolCalls?.length > 0 && (
                <div className="mcp-agent-tool-calls">
                  <strong>Tools invoked:</strong>
                  {item.toolCalls.map((call, callIndex) => (
                    <span key={`${call.tool}-${callIndex}`}>{call.tool}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {mcpLoading && <p className="mcp-agent-loading">Agent is thinking and executing tools...</p>}
        </div>

        {mcpError && <p className="mcp-agent-error" role="alert">{mcpError}</p>}

        <form className="mcp-agent-input" onSubmit={sendMCPMessage}>
          <textarea
            value={mcpQuestion}
            onChange={(event) => setMcpQuestion(event.target.value)}
            placeholder="Ask the MCP-powered agent..."
            rows={2}
            disabled={mcpLoading}
          />
          <button type="submit" disabled={mcpLoading || !mcpQuestion.trim()}>
            {mcpLoading ? "Processing..." : "Send"}
          </button>
        </form>
      </section>

      <footer className="footer">
        React + FastAPI + LangChain + Amazon Bedrock + PostgreSQL + pgvector
      </footer>

      {/* Conversation Memory and Chat History */}

<section className="card conversation-card">

  <h2>AI Conversational Assistant</h2>

  <div className="chat-layout">

    <aside className="chat-sidebar">

      <button onClick={createChatSession} disabled={creatingSession}>
        {creatingSession ? "Creating..." : "+ New Conversation"}
      </button>

      <h3>Chat History</h3>

      {chatSessions.map((session) => (
        <button
          key={session.id}
          className={
            activeSessionId === session.id
              ? "session-button active"
              : "session-button"
          }
          onClick={() => openChatSession(session.id)}
        >
          {session.title}
        </button>
      ))}

    </aside>

    <div className="chat-window">

      <div className="chat-messages">

        {chatMessages.length === 0 && (
          <p className="chat-empty">
            Start a new conversation and ask a question.
          </p>
        )}

        {chatMessages.map((message, index) => (
          <div
            key={message.id || `pending-${index}`}
            className={`chat-message ${message.role}`}
          >
            <strong>
              {message.role === "user" ? "You" : "AI Assistant"}
            </strong>

            <p>{message.content}</p>
          </div>
        ))}

        {chatLoading && (
          <p className="chat-loading">
            AI Assistant is thinking...
          </p>
        )}

      </div>

      <div className="chat-input-area">

        <textarea
          value={chatQuestion}
          onChange={(e) => setChatQuestion(e.target.value)}
          placeholder="Ask a question or follow-up..."
          rows={2}
          disabled={!activeSessionId || chatLoading}
        />

        <button
          onClick={sendChatMessage}
          disabled={!activeSessionId || chatLoading || !chatQuestion.trim()}
        >
          {chatLoading ? "Sending..." : "Send"}
        </button>

      </div>

    </div>

  </div>

</section>

    </div>
  );
}

export default App;