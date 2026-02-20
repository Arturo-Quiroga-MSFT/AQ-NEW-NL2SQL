import { useState, useRef, useEffect } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";

/** Lightweight markdown→HTML for admin answers (headers, bold, bullets, code blocks). */
function simpleMarkdown(md: string): string {
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="sql-block">$2</pre>')
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^\- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/\n{2,}/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}

interface Message {
  role: "user" | "assistant";
  question: string;
  mode?: "data_query" | "admin_assist";
  model?: string;
  sql?: string;
  columns?: string[];
  rows?: (string | number | null)[][];
  answer?: string;
  error?: string | null;
  retries?: number;
  elapsed_ms?: number;
  tokens_in?: number;
  tokens_out?: number;
  tokens_total?: number;
}

const MODEL_OPTIONS = [
  { value: "gpt-4.1", label: "GPT-4.1" },
  { value: "gpt-5.2-low", label: "GPT-5.2 (low reasoning)" },
  { value: "gpt-5.2-medium", label: "GPT-5.2 (medium reasoning)" },
];

function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState<number | null>(null);
  const [model, setModel] = useState("gpt-4.1");
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
        body: JSON.stringify({ question, session_id: sessionId, model }),
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          question: data.question,
          mode: data.mode,
          model: data.model,
          sql: data.sql,
          columns: data.columns,
          rows: data.rows,
          answer: data.answer,
          error: data.error,
          retries: data.retries,
          elapsed_ms: data.elapsed_ms,
          tokens_in: data.tokens_in,
          tokens_out: data.tokens_out,
          tokens_total: data.tokens_total,
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

  const handleSaveChat = () => {
    if (messages.length === 0) return;
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const lines: string[] = [`# NL2SQL Chat — ${new Date().toLocaleString()}\n`];

    messages.forEach((msg) => {
      if (msg.role === "user") {
        lines.push(`## Q: ${msg.question}\n`);
      } else if (msg.error) {
        lines.push(`**Error:** ${msg.error}\n`);
      } else if (msg.mode === "admin_assist") {
        lines.push(msg.answer || "");
        lines.push("");
      } else {
        lines.push("```sql");
        lines.push(msg.sql || "");
        lines.push("```\n");
        if (msg.columns && msg.rows && msg.rows.length > 0) {
          lines.push(`| ${msg.columns.join(" | ")} |`);
          lines.push(`| ${msg.columns.map(() => "---").join(" | ")} |`);
          msg.rows.forEach((row) => {
            lines.push(`| ${row.map((c) => (c === null ? "NULL" : String(c))).join(" | ")} |`);
          });
          lines.push(`\n*${msg.rows.length} row${msg.rows.length !== 1 ? "s" : ""}*\n`);
        }
      }
    });

    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nl2sql-chat-${ts}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <h1>NL2SQL</h1>
          <span className="subtitle">RetailDW &middot; Azure SQL</span>
          <select
            className="model-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {MODEL_OPTIONS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <button className="new-btn" onClick={handleNewSession}>
            New Chat
          </button>
          {messages.length > 0 && (
            <button className="save-btn" onClick={handleSaveChat}>
              Save Chat
            </button>
          )}
        </div>
        <div className="header-desc">
          <div><span className="mode-label data-pill">Data Query</span> Ask questions in plain English and get SQL + results from the RetailDW database.</div>
          <div><span className="mode-label admin-pill">DB Assistant</span> Ask about schema, relationships, indexes, design, or best practices — answered directly, no SQL needed.</div>
          <div className="header-schema">
            <strong>RetailDW</strong> — E-Commerce star schema &middot;
            7 dimensions &middot; 5 fact tables &middot; 4 analytical views &middot;
            ~21K rows &middot; 20 foreign keys &middot;
            Orders, Returns, Reviews, Web Traffic, Inventory
          </div>
        </div>
      </header>

      <main className="chat">
        <div className="welcome">
          <p className="welcome-title">Ask anything about the RetailDW database in plain English</p>
          <p className="welcome-sub">Query your data, explore the schema, or get DBA advice — all in one chat.</p>

          <div className="suggestion-group">
            <span className="sg-label data-pill">Data Queries</span>
            <div className="suggestions">
              {[
                "What are the top 5 products by revenue?",
                "Show monthly sales for 2024",
                "Which customers have the most returns?",
                "Average order value by store",
              ].map((q) => (
                <button key={q} className="suggestion" onClick={() => setInput(q)}>{q}</button>
              ))}
            </div>
          </div>

          <div className="suggestion-group">
            <span className="sg-label admin-pill">Schema &amp; DB Assistant</span>
            <div className="suggestions">
              {[
                "What tables are in the database?",
                "Describe the DimCustomer table",
                "How are orders related to products?",
                "Suggest indexes for FactOrders",
              ].map((q) => (
                <button key={q} className="suggestion" onClick={() => setInput(q)}>{q}</button>
              ))}
            </div>
          </div>

          <div className="suggestion-group">
            <span className="sg-label feat-pill">Follow-ups &amp; Multi-turn</span>
            <div className="suggestions">
              {[
                "Show monthly sales for 2024  →  now for 2025",
                "Top 10 products  →  filter by Clothing",
              ].map((q) => (
                <button key={q} className="suggestion suggestion-hint" disabled>{q}</button>
              ))}
            </div>
          </div>
        </div>

        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="msg user-msg">
              <div className="bubble user-bubble">{msg.question}</div>
            </div>
          ) : (
            <div key={i} className="msg assistant-msg">
              <div className={`bubble assistant-bubble ${msg.mode === "admin_assist" ? "admin-bubble" : ""}`}>
                {msg.error ? (
                  <div className="error">{msg.error}</div>
                ) : msg.mode === "admin_assist" ? (
                  <div className="admin-answer">
                    <span className="mode-badge admin-badge">DB Assistant</span>
                    {msg.model && <span className="mode-badge model-badge">{msg.model}</span>}
                    <div className="markdown-body" dangerouslySetInnerHTML={{ __html: simpleMarkdown(msg.answer || "") }} />
                  </div>
                ) : (
                  <>
                    <span className="mode-badge query-badge">Data Query</span>
                    {msg.model && <span className="mode-badge model-badge">{msg.model}</span>}
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
                {msg.elapsed_ms != null && msg.elapsed_ms > 0 && (
                  <div className="stats-line">
                    ⏱ {(msg.elapsed_ms / 1000).toFixed(1)}s
                    {msg.tokens_total != null && msg.tokens_total > 0 && (
                      <> &middot; tokens: {msg.tokens_in?.toLocaleString()} in / {msg.tokens_out?.toLocaleString()} out / {msg.tokens_total?.toLocaleString()} total</>
                    )}
                  </div>
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
          placeholder="Ask about your data or database structure…"
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
