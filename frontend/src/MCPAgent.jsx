import { useState } from "react";
import "./MCPAgent.css";

const API_URL = "http://127.0.0.1:8000/api/mcp-agent/ask";

function MCPAgent() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const sendMessage = async (event) => {
    event.preventDefault();

    const userQuestion = question.trim();

    if (!userQuestion || loading) {
      return;
    }

    setError("");
    setQuestion("");

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: userQuestion,
      },
    ]);

    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: userQuestion,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to get an answer from the agent."
        );
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
          toolCalls: data.tool_calls || [],
        },
      ]);
    } catch (err) {
      setError(err.message || "Something went wrong.");

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: "I could not process your request.",
          toolCalls: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mcp-agent">
      <div className="mcp-header">
        <div>
          <h2>VPRO MCP Agent</h2>
          <p>Powered by LangGraph, Amazon Bedrock and MCP</p>
        </div>
        <span className="mcp-status">Agent Ready</span>
      </div>

      <div className="mcp-messages">
        {messages.length === 0 && (
          <div className="mcp-welcome">
            <h3>Welcome to VPRO Skills AI Agent</h3>
            <p>
              Ask questions, perform calculations or search your
              uploaded course documents.
            </p>

            <div className="mcp-examples">
              <button
                type="button"
                onClick={() =>
                  setQuestion(
                    "Calculate 250 multiplied by 4 plus 150."
                  )
                }
              >
                Calculate 250 × 4 + 150
              </button>

              <button
                type="button"
                onClick={() =>
                  setQuestion(
                    "What are the main features of Python? Use my uploaded knowledge documents."
                  )
                }
              >
                Search Python knowledge
              </button>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            className={`mcp-message ${message.role}`}
            key={index}
          >
            <div className="mcp-role">
              {message.role === "user" ? "You" : "VPRO AI Agent"}
            </div>

            <div className="mcp-message-content">
              {message.content}
            </div>

            {message.toolCalls?.length > 0 && (
              <div className="mcp-tool-info">
                <strong>Tools invoked:</strong>

                {message.toolCalls.map((tool, toolIndex) => (
                  <div key={toolIndex}>
                    {tool.tool}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="mcp-loading">
            Agent is thinking and executing tools...
          </div>
        )}

        {error && (
          <div className="mcp-error">
            {error}
          </div>
        )}
      </div>

      <form className="mcp-input-area" onSubmit={sendMessage}>
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask your question..."
          disabled={loading}
        />

        <button
          type="submit"
          disabled={loading || !question.trim()}
        >
          {loading ? "Processing..." : "Send"}
        </button>
      </form>
    </div>
  );
}

export default MCPAgent;