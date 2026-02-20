import { useState, useRef, useEffect } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  question: string;
  sql?: string;
  columns?: string[];
  rows?: (string | number | null)[][];
  error?: string | null;
  retries?: number;
}

function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", question }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }),
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          question: data.question,
          sql: data.sql,
          columns: data.columns,
          rows: data.rows,
          error: data.error,
          retries: data.retries,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", question, error: String(err) },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    setMessages([]);
    setSessionId(null);
    setShowSql(null);
    if (sessionId) {
      fetch(`${API_BASE}/api/session/${sessionId}`, { method: "DELETE" });
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>NL2SQL</h1>
        <span className="subtitle">RetailDW &middot; Azure SQL &middot; gpt-4.1</span>
        <button className="new-btn" onClick={handleNewSession}>
          New Chat
        </button>
      </header>

      <main className="chat">
        {messages.length === 0 && (
          <div className="empty">
            <p>Ask a question about the RetailDW database in plain English.</p>
            <div className="suggestions">
              {[
                "What are the top 5 products by revenue?",
                "Show monthly sales for 2024",
                "Which customers have the most returns?",
                "What's the average order value by store?",
              ].map((q) => (
                <button
                  key={q}
                  className="suggestion"
                  onClick={() => {
                    setInput(q);
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="msg user-msg">
              <div className="bubble user-bubble">{msg.question}</div>
            </div>
          ) : (
            <div key={i} className="msg assistant-msg">
              <div className="bubble assistant-bubble">
                {msg.error ? (
                  <div className="error">{msg.error}</div>
                ) : (
                  <>
                    <button
                      className="sql-toggle"
                      onClick={() => setShowSql(showSql === i ? null : i)}
                    >
                      {showSql === i ? "Hide SQL" : "Show SQL"}
                      {msg.retries ? ` (${msg.retries} retries)` : ""}
                    </button>
                    {showSql === i && (
                      <pre className="sql-block">{msg.sql}</pre>
                    )}
                    {msg.columns && msg.rows && msg.rows.length > 0 ? (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              {msg.columns.map((c) => (
                                <th key={c}>{c}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {msg.rows.map((row, ri) => (
                              <tr key={ri}>
                                {row.map((cell, ci) => (
                                  <td key={ci}>
                                    {cell === null ? (
                                      <span className="null">NULL</span>
                                    ) : (
                                      String(cell)
                                    )}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        <div className="row-count">
                          {msg.rows.length} row{msg.rows.length !== 1 ? "s" : ""}
                        </div>
                      </div>
                    ) : (
                      <div className="no-results">No results</div>
                    )}
                  </>
                )}
              </div>
            </div>
          )
        )}

        {loading && (
          <div className="msg assistant-msg">
            <div className="bubble assistant-bubble loading-bubble">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      <form className="input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your data…"
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

export default App;
