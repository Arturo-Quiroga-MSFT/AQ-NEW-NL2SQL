import { useState, useRef, useEffect } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
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
  chart_type?: "bar" | "line" | "pie" | "none";
  x_col?: string;
  y_col?: string;
  // Approval fields
  approval_id?: string | null;
  approval_tool?: string | null;
  approval_sql?: string | null;
  approval_explanation?: string | null;
  approval_status?: "pending" | "approved" | "rejected" | "resolving";
  approval_result?: string;
}

const CHART_COLORS = ["#e94560", "#4ecca3", "#79c0ff", "#f5a623", "#bd93f9", "#ff79c6", "#50fa7b", "#ffb86c"];

const TOOLTIP_STYLE = { background: "#16213e", border: "1px solid #0f3460", color: "#e0e0e0", borderRadius: 6, fontSize: "0.8rem" };

function ChartPanel({ chartType, columns, rows, xCol, yCol }: {
  chartType: "bar" | "line" | "pie";
  columns: string[];
  rows: (string | number | null)[][];
  xCol: string;
  yCol: string;
}) {
  const data = rows.map((row) => {
    const obj: Record<string, unknown> = {};
    columns.forEach((col, i) => { obj[col] = row[i]; });
    return obj;
  });

  if (chartType === "bar") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" />
          <XAxis dataKey={xCol} tick={{ fill: "#aaa", fontSize: 11 }} interval={0} angle={data.length > 8 ? -35 : 0} textAnchor={data.length > 8 ? "end" : "middle"} height={data.length > 8 ? 80 : 40} />
          <YAxis tick={{ fill: "#aaa", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey={yCol} fill="#e94560" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" />
          <XAxis dataKey={xCol} tick={{ fill: "#aaa", fontSize: 11 }} />
          <YAxis tick={{ fill: "#aaa", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey={yCol} stroke="#4ecca3" strokeWidth={2} dot={{ fill: "#4ecca3", r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  // pie
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie data={data} dataKey={yCol} nameKey={xCol} cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: "0.75rem", color: "#aaa" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function ApprovalCard({ msg, index, onAction }: {
  msg: Message;
  index: number;
  onAction: (index: number, action: "approve" | "reject") => void;
}) {
  const status = msg.approval_status || "pending";
  const isPending = status === "pending";
  const isResolving = status === "resolving";

  return (
    <div className={`approval-card approval-${status}`}>
      <div className="approval-header">
        <span className="approval-icon">{status === "approved" ? "\u2705" : status === "rejected" ? "\u274C" : "\u26A0\uFE0F"}</span>
        <span className="approval-title">
          {status === "approved" ? "Approved" : status === "rejected" ? "Rejected" : "Write Operation \u2014 Approval Required"}
        </span>
      </div>
      {msg.approval_tool && (
        <div className="approval-tool">Tool: <code>{msg.approval_tool}</code></div>
      )}
      {msg.approval_sql && (
        <pre className="approval-sql">{msg.approval_sql}</pre>
      )}
      {msg.approval_explanation && (
        <div className="approval-explanation"
             dangerouslySetInnerHTML={{ __html: simpleMarkdown(msg.approval_explanation) }} />
      )}
      {(isPending || isResolving) && (
        <div className="approval-actions">
          <button
            className="approval-btn approve-btn"
            onClick={() => onAction(index, "approve")}
            disabled={isResolving}
          >
            {isResolving ? "Processing\u2026" : "\u2705 Approve"}
          </button>
          <button
            className="approval-btn reject-btn"
            onClick={() => onAction(index, "reject")}
            disabled={isResolving}
          >
            \u274C Reject
          </button>
        </div>
      )}
      {msg.approval_result && (
        <div className="approval-result">
          <div className="markdown-body"
               dangerouslySetInnerHTML={{ __html: simpleMarkdown(msg.approval_result) }} />
        </div>
      )}
    </div>
  );
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
  const [tableView, setTableView] = useState<Set<number>>(new Set());
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
          chart_type: data.chart_type,
          x_col: data.x_col,
          y_col: data.y_col,
          approval_id: data.approval_id,
          approval_tool: data.approval_tool,
          approval_sql: data.approval_sql,
          approval_explanation: data.approval_explanation,
          approval_status: data.approval_id ? "pending" : undefined,
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

  const handleApproval = async (index: number, action: "approve" | "reject") => {
    const msg = messages[index];
    if (!msg.approval_id) return;

    // Mark as resolving
    setMessages((prev) => prev.map((m, i) =>
      i === index ? { ...m, approval_status: "resolving" as const } : m
    ));

    try {
      const res = await fetch(`${API_BASE}/api/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approval_id: msg.approval_id, action }),
      });
      const data = await res.json();

      setMessages((prev) => prev.map((m, i) =>
        i === index
          ? {
              ...m,
              approval_status: action === "approve" ? "approved" as const : "rejected" as const,
              approval_result: data.error || data.answer,
              elapsed_ms: (m.elapsed_ms || 0) + (data.elapsed_ms || 0),
              tokens_in: (m.tokens_in || 0) + (data.tokens_in || 0),
              tokens_out: (m.tokens_out || 0) + (data.tokens_out || 0),
              tokens_total: (m.tokens_total || 0) + (data.tokens_total || 0),
            }
          : m
      ));
    } catch (err) {
      setMessages((prev) => prev.map((m, i) =>
        i === index
          ? { ...m, approval_status: "rejected" as const, approval_result: String(err) }
          : m
      ));
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
                ) : msg.approval_id ? (
                  <div className="admin-answer">
                    <span className="mode-badge admin-badge">DB Assistant</span>
                    {msg.model && <span className="mode-badge model-badge">{msg.model}</span>}
                    <ApprovalCard msg={msg} index={i} onAction={handleApproval} />
                  </div>
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
                      <>
                        {msg.chart_type && msg.chart_type !== "none" && msg.x_col && msg.y_col && (
                          <div className="chart-toggle-bar">
                            <button
                              className={`chart-tab ${!tableView.has(i) ? "chart-tab-active" : ""}`}
                              onClick={() => setTableView((s) => { const n = new Set(s); n.delete(i); return n; })}
                            >📊 Chart</button>
                            <button
                              className={`chart-tab ${tableView.has(i) ? "chart-tab-active" : ""}`}
                              onClick={() => setTableView((s) => new Set(s).add(i))}
                            >📋 Table</button>
                          </div>
                        )}
                        {msg.chart_type && msg.chart_type !== "none" && msg.x_col && msg.y_col && !tableView.has(i) ? (
                          <div className="chart-container">
                            <ChartPanel
                              chartType={msg.chart_type as "bar" | "line" | "pie"}
                              columns={msg.columns}
                              rows={msg.rows}
                              xCol={msg.x_col}
                              yCol={msg.y_col}
                            />
                          </div>
                        ) : (
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
                          </div>
                        )}
                        <div className="row-count">
                          {msg.rows.length} row{msg.rows.length !== 1 ? "s" : ""}
                        </div>
                      </>
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
