import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const QUICK = [
  "What are the main features of Python?",
  "Explain a topic in simple words",
  "Summarise my course notes",
];

export default function ChatWidget({ onOpenFull }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy, open]);

  async function send(question) {
    const q = (question ?? text).trim();
    if (!q || busy) return;
    setText("");
    setError("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: q }]);
    try {
      let id = sessionId;
      if (!id) {
        id = (await api("/api/chat/sessions", { method: "POST" })).id;
        setSessionId(id);
      }
      const data = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ session_id: id, question: q }),
      });
      const files = [...new Set((data.sources || []).map((s) => s.filename))];
      setMessages((m) => [...m, { role: "assistant", content: data.answer, files }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setMessages([]);
    setSessionId(null);
    setError("");
  }

  return (
    <div className="cw">
      {open && (
        <section className="cw-panel" aria-label="VPRO AI chat">
          <header className="cw-head">
            <div className="cw-avatar">AI</div>
            <div className="cw-title">
              <strong>VPRO Study Buddy</strong>
              <small><i /> Online · ready to help</small>
            </div>
            <button className="cw-icon" onClick={reset} title="Start a new chat" aria-label="New chat">↻</button>
            <button className="cw-icon" onClick={() => setOpen(false)} aria-label="Close chat">✕</button>
          </header>

          <div className="cw-body">
            {messages.length === 0 && (
              <div className="cw-welcome">
                <div className="cw-wave">👋</div>
                <h3>Hi there! I'm your Study Buddy.</h3>
                <p>Ask me anything about your course. I'll answer from your study material.</p>
                <div className="cw-quick">
                  {QUICK.map((q) => (
                    <button key={q} onClick={() => send(q)}>{q}</button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`cw-msg ${m.role}`}>
                <div className="cw-bubble">
                  {m.content}
                  {m.files?.length > 0 && <span className="cw-src">📄 {m.files.join(", ")}</span>}
                </div>
              </div>
            ))}

            {busy && (
              <div className="cw-msg assistant">
                <div className="cw-bubble typing"><span /> <span /> <span /></div>
              </div>
            )}
            {error && <div className="alert alert-error">{error}</div>}
            <div ref={endRef} />
          </div>

          <form className="cw-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type your question…"
              disabled={busy}
              aria-label="Your question"
            />
            <button type="submit" disabled={busy || !text.trim()} aria-label="Send">➤</button>
          </form>
          <button className="cw-full" onClick={() => { setOpen(false); onOpenFull(); }}>
            Open full-screen chat with history →
          </button>
        </section>
      )}

      {!open && <div className="cw-hint">Need help with your studies? 👋</div>}
      <button className={`cw-launch ${open ? "is-open" : ""}`} onClick={() => setOpen((o) => !o)} aria-label={open ? "Close chat" : "Open chat"} aria-expanded={open}>
        {open ? "✕" : (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 8.6 8.6 0 0 1-3.6-.8L3 20l1.1-4.9A8.4 8.4 0 1 1 21 11.5z" />
          </svg>
        )}
      </button>
    </div>
  );
}