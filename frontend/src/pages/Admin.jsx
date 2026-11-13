import { useState } from "react";
import Harness from "../components/Harness";
import RagQuality from "../components/RagQuality";
import Content from "../components/Content";

const TABS = [
  { id: "harness", label: "Agent performance" },
  { id: "rag", label: "Answer quality (RAG)" },
  { id: "content", label: "Course content" },
];

// Demo-only login: it hides the UI but does not protect the backend API.
const ADMIN_USER = "admin@vproskills.com";
const ADMIN_PASS = "admin@123";

function Login({ onSignIn }) {
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");

  function submit(event) {
    event.preventDefault();
    if (user.trim() === ADMIN_USER && pass === ADMIN_PASS) onSignIn();
    else setError("Incorrect email or password.");
  }

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <h1 className="h2">Admin sign in</h1>
        <p className="muted">Sign in to view agent performance and manage course content.</p>
        <label htmlFor="u">Email</label>
        <input id="u" type="email" autoComplete="username" value={user} onChange={(e) => setUser(e.target.value)} required />
        <label htmlFor="p">Password</label>
        <input id="p" type="password" autoComplete="current-password" value={pass} onChange={(e) => setPass(e.target.value)} required />
        {error && <div className="alert alert-error">{error}</div>}
        <button className="btn btn-primary btn-block" type="submit">
          Sign in
        </button>
      </form>
    </div>
  );
}

export default function Admin({ isAdmin, onSignIn }) {
  const [tab, setTab] = useState("harness");

  if (!isAdmin) return <Login onSignIn={onSignIn} />;

  return (
    <div className="container page">
      <div className="page-head">
        <h1>Admin dashboard</h1>
        <p className="muted">Monitor how well your AI agent performs and manage what students can learn from.</p>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "harness" && <Harness />}
      {tab === "rag" && <RagQuality />}
      {tab === "content" && <Content />}
    </div>
  );
}