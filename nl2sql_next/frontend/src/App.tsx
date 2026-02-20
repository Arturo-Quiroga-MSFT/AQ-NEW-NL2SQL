import { useState, useRef, useEffect } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { toPng } from "html-to-image";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

/** Export a chart container to PNG and trigger download. */
function exportChartAsPng(container: HTMLElement, filename = "chart.png") {
  toPng(container, { pixelRatio: 2, backgroundColor: "#1a1a2e" })
    .then((dataUrl) => {
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = filename;
      a.click();
    })
    .catch((err) => console.error("Chart export failed:", err));
}

/** Lightweight markdown→HTML for admin answers (headers, bold, bullets, code blocks, tables). */
function simpleMarkdown(md: string): string {
  // First pass: extract code blocks to protect them from further processing
  const codeBlocks: string[] = [];
  let processed = md.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
    codeBlocks.push(`<pre class="sql-block">${code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`);
    return `%%CODEBLOCK_${codeBlocks.length - 1}%%`;
  });

  // Second pass: extract and convert markdown tables
  const tableBlocks: string[] = [];
  processed = processed.replace(
    /(^[ \t]*\|.+\|[ \t]*\n)([ \t]*\|[ \t:]*-[-| \t:]*\|[ \t]*\n)((?:[ \t]*\|.+\|[ \t]*\n?)*)/gm,
    (_match, headerLine: string, _separatorLine: string, bodyLines: string) => {
      const parseRow = (line: string) =>
        line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

      const headers = parseRow(headerLine);
      const rows = bodyLines
        .trim()
        .split("\n")
        .filter((l: string) => l.trim())
        .map((l: string) => parseRow(l));

      let html = '<div class="table-wrap"><table><thead><tr>';
      headers.forEach((h) => { html += `<th>${h}</th>`; });
      html += "</tr></thead><tbody>";
      rows.forEach((row) => {
        html += "<tr>";
        row.forEach((cell) => { html += `<td>${cell}</td>`; });
        html += "</tr>";
      });
      html += "</tbody></table></div>";

      tableBlocks.push(html);
      return `\n%%TABLEBLOCK_${tableBlocks.length - 1}%%\n`;
    }
  );

  // Third pass: normal inline markdown
  processed = processed
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^\- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/\n{2,}/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");

  // Restore code blocks and table blocks
  codeBlocks.forEach((html, i) => {
    processed = processed.replace(`%%CODEBLOCK_${i}%%`, html);
  });
  tableBlocks.forEach((html, i) => {
    processed = processed.replace(`%%TABLEBLOCK_${i}%%`, html);
  });

  return processed;
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
        <Pie data={data} dataKey={yCol} nameKey={xCol} cx="50%" cy="50%" outerRadius={100} label={(props: PieLabelRenderProps) => `${props.name ?? ""} ${((props.percent ?? 0) * 100).toFixed(0)}%`}>
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
  const [chartView, setChartView] = useState<Set<number>>(new Set());
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

    // Add placeholder assistant message for streaming
    const assistantIdx = messages.length + 1; // index after user msg
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        question,
        answer: "",
        mode: undefined,
        model: undefined,
        sql: "",
        columns: [],
        rows: [],
        error: null,
        elapsed_ms: 0,
        tokens_in: 0,
        tokens_out: 0,
        tokens_total: 0,
      },
    ]);

    try {
      const res = await fetch(`${API_BASE}/api/ask/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId, model }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6);
          if (!jsonStr) continue;

          let evt: Record<string, unknown>;
          try {
            evt = JSON.parse(jsonStr);
          } catch {
            continue;
          }

          const evtType = evt.type as string;

          if (evtType === "start") {
            const sid = evt.session_id as string;
            if (sid) setSessionId(sid);
            setMessages((prev) =>
              prev.map((m, i) =>
                i === assistantIdx
                  ? { ...m, mode: evt.mode as Message["mode"], model: evt.model as string }
                  : m
              )
            );
          } else if (evtType === "delta") {
            const text = evt.text as string;
            setMessages((prev) =>
              prev.map((m, i) =>
                i === assistantIdx
                  ? { ...m, answer: (m.answer || "") + text }
                  : m
              )
            );
          } else if (evtType === "tool_start") {
            // Tool activity — silently ignored (no visible indicator)
          } else if (evtType === "tool_done") {
            // Tool completed — no-op
          } else if (evtType === "approval") {
            setMessages((prev) =>
              prev.map((m, i) =>
                i === assistantIdx
                  ? {
                      ...m,
                      mode: "admin_assist" as const,
                      approval_id: evt.approval_id as string,
                      approval_tool: evt.approval_tool as string,
                      approval_sql: evt.approval_sql as string,
                      approval_explanation: evt.approval_explanation as string,
                      approval_status: "pending" as const,
                    }
                  : m
              )
            );
          } else if (evtType === "done") {
            setMessages((prev) =>
              prev.map((m, i) =>
                i === assistantIdx
                  ? {
                      ...m,
                      elapsed_ms: evt.elapsed_ms as number,
                      tokens_in: evt.tokens_in as number,
                      tokens_out: evt.tokens_out as number,
                      tokens_total: evt.tokens_total as number,
                    }
                  : m
              )
            );
          } else if (evtType === "full_response") {
            // Non-streaming data_query response — arrived as single event
            const sid = evt.session_id as string;
            if (sid) setSessionId(sid);
            setMessages((prev) =>
              prev.map((m, i) =>
                i === assistantIdx
                  ? {
                      ...m,
                      mode: evt.mode as Message["mode"],
                      model: evt.model as string,
                      sql: evt.sql as string,
                      columns: evt.columns as string[],
                      rows: evt.rows as (string | number | null)[][],
                      answer: evt.answer as string,
                      error: evt.error as string | null,
                      retries: evt.retries as number,
                      elapsed_ms: evt.elapsed_ms as number,
                      tokens_in: evt.tokens_in as number,
                      tokens_out: evt.tokens_out as number,
                      tokens_total: evt.tokens_total as number,
                      chart_type: evt.chart_type as Message["chart_type"],
                      x_col: evt.x_col as string,
                      y_col: evt.y_col as string,
                    }
                  : m
              )
            );
          } else if (evtType === "error") {
            setMessages((prev) =>
              prev.map((m, i) =>
                i === assistantIdx
                  ? { ...m, error: evt.message as string }
                  : m
              )
            );
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m, i) =>
          i === assistantIdx
            ? { ...m, error: String(err) }
            : m
        )
      );
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
          <img src="/microsoft-logo.svg" alt="Microsoft" className="ms-logo" />
          <h1>NL2SQL</h1>
          <span className="subtitle">Natural Language to SQL &middot; Azure OpenAI</span>
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
      </header>

      <main className="chat">
        <div className="welcome">
          <h2 className="welcome-headline">Your AI-Powered Database Assistant</h2>
          <p className="welcome-sub">
            Talk to your database in plain English. Ask complex analytical questions, explore your schema, 
            or manage administrative tasks — powered by Azure OpenAI with built-in safety guardrails.
          </p>

          <div className="feature-cards">
            <div className="feature-card feature-card-data">
              <div className="feature-icon">📊</div>
              <h3 className="feature-title">Data Insights</h3>
              <p className="feature-desc">
                Ask questions in plain English and get instant SQL queries, result tables, and interactive charts 
                from your database. Multi-turn conversations let you drill down and refine results.
              </p>
              <div className="feature-examples">
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

            <div className="feature-card feature-card-admin">
              <div className="feature-icon">🛠️</div>
              <h3 className="feature-title">DB Administration</h3>
              <p className="feature-desc">
                Explore schema details, check relationships, get index recommendations, and execute admin 
                operations — with approval safeguards for any write actions.
              </p>
              <div className="feature-examples">
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
          </div>

          <div className="welcome-schema">
            <strong>RetailDW</strong> — E-Commerce star schema &middot;
            7 dimensions &middot; 5 fact tables &middot; 4 analytical views &middot;
            ~50K rows &middot; 20 foreign keys &middot;
            Orders, Returns, Reviews, Web Traffic, Inventory
          </div>

          <div className="welcome-hint">
            <span className="feat-pill" style={{fontSize: '0.65rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600}}>Multi-turn</span>
            <span className="welcome-hint-text">Ask a follow-up to refine any answer — e.g. "now filter by Clothing" or "show that as a chart"</span>
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
                              className={`chart-tab ${!chartView.has(i) ? "chart-tab-active" : ""}`}
                              onClick={() => setChartView((s) => { const n = new Set(s); n.delete(i); return n; })}
                            >📋 Table</button>
                            <button
                              className={`chart-tab ${chartView.has(i) ? "chart-tab-active" : ""}`}
                              onClick={() => setChartView((s) => new Set(s).add(i))}
                            >📊 Chart</button>
                          </div>
                        )}
                        {msg.chart_type && msg.chart_type !== "none" && msg.x_col && msg.y_col && chartView.has(i) ? (
                          <div className="chart-container" ref={(el) => { if (el) el.dataset.chartIndex = String(i); }}>
                            <ChartPanel
                              chartType={msg.chart_type as "bar" | "line" | "pie"}
                              columns={msg.columns}
                              rows={msg.rows}
                              xCol={msg.x_col}
                              yCol={msg.y_col}
                            />
                            <button
                              className="chart-export-btn"
                              title="Download chart as PNG"
                              onClick={(e) => {
                                const container = (e.target as HTMLElement).closest(".chart-container");
                                if (container) exportChartAsPng(container as HTMLElement, `chart-${i + 1}.png`);
                              }}
                            >📷 Export PNG</button>
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

        {loading && messages.length > 0 && (() => {
          const lastMsg = messages[messages.length - 1];
          // Only show loading dots if the last message is a user message (no assistant placeholder yet)
          // or if it's a data_query assistant placeholder with no data yet
          const isStreamingAdmin = lastMsg.role === "assistant" && lastMsg.mode === "admin_assist" && lastMsg.answer;
          if (isStreamingAdmin) return null;
          return (
            <div className="msg assistant-msg">
              <div className="bubble assistant-bubble loading-bubble">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          );
        })()}
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
