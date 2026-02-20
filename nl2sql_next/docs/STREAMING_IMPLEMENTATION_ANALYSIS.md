

 No streaming is implemented. The current flow is fully synchronous: frontend `fetch()` → FastAPI endpoint → `client.responses.create()` (blocking) → JSON response back. The user sees nothing until the entire pipeline completes.

### How hard?

**Medium effort** — roughly a day of focused work across 3 layers:

| Layer | What changes | Effort |
|-------|-------------|--------|
| **Backend (LLM call)** | Switch `client.responses.create()` → `client.responses.create(stream=True)`, iterate over SSE events | Small — SDK supports it natively |
| **Backend (API)** | Change `/api/ask` to return a `StreamingResponse` (SSE), yield chunks as they arrive | Medium — need to handle both `data_query` and `admin_assist` paths, plus tool-use loop interruptions |
| **Frontend** | Replace `fetch` + `response.json()` with `EventSource` or `fetch` + `ReadableStream`, append tokens incrementally to the chat bubble | Medium — state management for partial markdown rendering |

### Where it gets tricky

1. **The data_query path has multiple stages**: router → SQL generation → execution → (optional retries). Streaming the SQL generation is useful, but you'd also want status indicators like "Routing…", "Generating SQL…", "Executing…" — that's an event protocol, not just token streaming.

2. **The admin tool-use loop** is the hardest part. The LLM streams text, then emits a tool call, you execute the tool, then the LLM streams more text. You'd need to handle interleaved text chunks and tool-call events, including the approval pause.

3. **Save Chat / results** — currently captures the final markdown. With streaming, you'd need to buffer the complete response for saving.

4. **Charts and tables** — the frontend renders charts/tables only after the full result is available (needs columns + rows). Streaming doesn't help here since the SQL result comes as a batch from pyodbc anyway.

### Pros

- **Perceived latency drops dramatically** — users see the first token in ~200ms instead of waiting 3-8s for the full response
- **Better UX for admin assistant** — long markdown answers feel much snappier
- **Progress feedback** — can show "Thinking…" → "Calling tools…" → streaming text

### Cons

- **Complexity** — SSE protocol, partial state management, error handling mid-stream
- **Tool-use + approval flow** — interleaving streaming with approval pauses requires careful state management
- **SQL results don't benefit** — the table/chart data comes from pyodbc in one shot; streaming only helps the LLM text portions
- **Testing** — harder to test than synchronous JSON responses
- **ACA deployment** — need to verify ACA supports long-lived SSE connections (it does, but timeout config matters)

### Recommendation

**Worth doing, but do it in phases:**

1. **Phase A**: Stream the admin assistant text responses only (biggest UX win, simplest path — no SQL execution or charts involved)
2. **Phase B**: Add structured status events to the data_query path ("routing", "generating_sql", "executing", "done") — not token streaming, just progress indicators
3. **Phase C**: Stream the SQL generation tokens if desired (lower priority — SQL generation is fast with gpt-4.1)

