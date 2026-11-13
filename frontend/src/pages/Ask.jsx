import { useEffect, useRef, useState } from "react";
import { api, toolLabel } from "../api";

const SUGGESTIONS = {
  course: [
    "What are the main features of Python?",
    "Explain the topic in simple words.",
    "Give me a short summary of my course notes.",
  ],
  agent: [
    "Calculate 250 multiplied by 4 plus 150.",
    "Search my course documents for Python features.",
  ],
};

export default function Ask() {
  const [mode, setMode] = useState("course");
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [agentMessages, setAgentMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  const shown = mode === "course" ? messages : agentMessages;

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [shown.length, busy]);

  async function loadSessions() {
    try {
      const data = await api("/api/chat/sessions");
      setSessions(Array.isArray(data) ? data : []);
    } catch {
      setSessions([]);
    }
  }

  async function openSession(id) {
    setMode("course");
    setError("");
    try {
      const data = await api(`/api/chat/sessions/${id}/messages`);
      setSessionId(id);
      setMessages(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    }
  }

  function newChat() {
    setError("");
    if (mode === "course") {
      setSessionId(null);
      setMessages([]);
    } else {
      setAgentMessages([]);
    }
  }

  async function send(question) {
    const q = (question ?? text).trim();
    if (!q || busy) return;
    setText("");
    setError("");
    setBusy(true);

    const add = mode === "course" ? setMessages : setAgentMessages;
    add((prev) => [...prev, { role: "user", content: q }]);

    try {
      if (mode === "course") {
        let id = sessionId;
        if (!id) {
          const created = await api("/api/chat/sessions", { method: "POST" });
          id = created.id;
          setSessionId(id);
        }
        const data = await api("/api/chat", {
          method: "POST",
          body: JSON.stringify({ session_id: id, question: q }),
        });
        const files = [...new Set((data.sources || []).map((s) => s.filename))];
        add((prev) => [...prev, { role: "assistant", content: data.answer, files }]);
        loadSessions();
      } else {
        const data = await api("/api/mcp-agent/ask", {
          method: "POST",
          body: JSON.stringify({ question: q }),
        });
        const tools = [...new Set((data.tool_calls || []).map((c) => toolLabel(c.tool || c.name)))];
        add((prev) => [
          ...prev,
          { role: "assistant", content: data.answer || "No answer was returned.", tools },
        ]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function onKey(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  return (
    <div className="ask">
      <aside className="ask-side">
        <button className="btn btn-primary btn-block" onClick={newChat}>
          + New chat
        </button>
        <div className="side-label">Your conversations</div>
        <div className="side-list">
          {sessions.length === 0 && <p className="muted small">No saved conversations yet.</p>}
          {sessions.map((s) => (
            <button
              key={s.id}
              className={mode === "course" && sessionId === s.id ? "active" : ""}
              onClick={() => openSession(s.id)}
              title={s.title}
            >
              {s.title || `Conversation ${s.id}`}
            </button>
          ))}
        </div>
      </aside>

      <section className="ask-main">
        <div className="ask-top">
          <div className="segmented" role="tablist" aria-label="Assistant mode">
            <button
              role="tab"
              aria-selected={mode === "course"}
              className={mode === "course" ? "active" : ""}
              onClick={() => setMode("course")}
            >
              Course Q&amp;A
            </button>
            <button
              role="tab"
              aria-selected={mode === "agent"}
              className={mode === "agent" ? "active" : ""}
              onClick={() => setMode("agent")}
            >
              AI Agent
            </button>
          </div>
          <p className="muted small">
            {mode === "course"
              ? "Answers come from your course documents and are saved in your history."
              : "The agent can use tools such as a calculator and course search."}
          </p>
        </div>

        <div className="thread">
          {shown.length === 0 && (
            <div className="empty-chat">
              <h2>What would you like to learn?</h2>
              <p>Pick a suggestion or type your own question below.</p>
              <div className="chips">
                {SUGGESTIONS[mode].map((s) => (
                  <button key={s} onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {shown.map((m, i) => (
            <div key={m.id || i} className={`msg ${m.role}`}>
              <div className="msg-avatar">{m.role === "user" ? "You" : "AI"}</div>
              <div className="msg-body">
                <p>{m.content}</p>
                {m.files?.length > 0 && (
                  <div className="msg-meta">
                    Source: {m.files.join(", ")}
                  </div>
                )}
                {m.tools?.length > 0 && (
                  <div className="msg-meta">Used: {m.tools.join(", ")}</div>
                )}
              </div>
            </div>
          ))}

          {busy && (
            <div className="msg assistant">
              <div className="msg-avatar">AI</div>
              <div className="msg-body typing">
                <span /> <span /> <span />
              </div>
            </div>
          )}
          {error && <div className="alert alert-error">{error}</div>}
          <div ref={endRef} />
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
            placeholder="Type your question…"
            rows={1}
            disabled={busy}
          />
          <button className="btn btn-primary" type="submit" disabled={busy || !text.trim()}>
            Send
          </button>
        </form>
        <p className="disclaimer">AI can make mistakes. Check important information with your instructor.</p>
      </section>
    </div>
  );
}