"""FastAPI backend for NL2SQL.

Run:
    cd nl2sql_next && uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure nl2sql_next is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.nl2sql import Conversation, ask as ask_single, resume_after_approval
from core.schema import get_schema_context

app = FastAPI(title="NL2SQL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory conversation store ────────────────────────
_conversations: Dict[str, Conversation] = {}

# ── Pending approvals store ───────────────────────────
_pending_approvals: Dict[str, Dict[str, Any]] = {}


def _get_conv(session_id: str) -> Conversation:
    if session_id not in _conversations:
        _conversations[session_id] = Conversation()
    return _conversations[session_id]


# ── Request/response models ─────────────────────────────

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    model: Optional[str] = None  # e.g. "gpt-4.1", "gpt-5.2-low", "gpt-5.2-medium"


class AskResponse(BaseModel):
    session_id: str
    question: str
    mode: str  # "data_query" or "admin_assist"
    model: str  # model key used for this response
    sql: str
    columns: List[str]
    rows: List[List[Any]]
    answer: str  # admin_assist text answer (empty for data_query)
    error: Optional[str]
    retries: int
    elapsed_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_total: int = 0
    chart_type: str = "none"  # "bar", "line", "pie", or "none"
    x_col: str = ""
    y_col: str = ""
    # Approval fields (non-null when a write tool needs user confirmation)
    approval_id: Optional[str] = None
    approval_tool: Optional[str] = None
    approval_sql: Optional[str] = None
    approval_explanation: Optional[str] = None


class HistoryItem(BaseModel):
    question: str
    sql: str = ""
    answer: str = ""


class ApproveRequest(BaseModel):
    approval_id: str
    action: str  # "approve" or "reject"


class ApproveResponse(BaseModel):
    approval_id: str
    action: str
    answer: str
    error: Optional[str] = None
    elapsed_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_total: int = 0


# ── Routes ──────────────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
def api_ask(req: AskRequest):
    """Ask a natural language question. Optionally pass session_id for multi-turn."""
    session_id = req.session_id or str(uuid.uuid4())
    conv = _get_conv(session_id)
    result = conv.ask(req.question, model_key=req.model)

    # Serialize Decimal/date values for JSON
    rows = _serialize_rows(result.get("rows", []))

    # Handle pending approval from tool-use loop
    approval = result.get("approval")
    approval_id = None
    approval_tool = None
    approval_sql = None
    approval_explanation = None

    if approval:
        approval_id = str(uuid.uuid4())
        approval_tool = approval.get("tool_name", "")
        try:
            args = json.loads(approval.get("tool_arguments", "{}"))
            approval_sql = args.get("sql", "")
        except (json.JSONDecodeError, TypeError):
            approval_sql = approval.get("tool_arguments", "")
        approval_explanation = approval.get("explanation", "")

        # Store the pending approval for later resume
        _pending_approvals[approval_id] = {
            "session_id": session_id,
            "pending": approval,
            "created_at": time.time(),
        }

    return AskResponse(
        session_id=session_id,
        question=result["question"],
        mode=result.get("mode", "data_query"),
        model=result.get("model", "gpt-4.1"),
        sql=result["sql"],
        columns=result.get("columns", []),
        rows=rows,
        answer=result.get("answer", ""),
        error=result.get("error"),
        retries=result.get("retries", 0),
        elapsed_ms=result.get("elapsed_ms", 0),
        tokens_in=result.get("tokens_in", 0),
        tokens_out=result.get("tokens_out", 0),
        tokens_total=result.get("tokens_total", 0),
        chart_type=result.get("chart_type", "none"),
        x_col=result.get("x_col", ""),
        y_col=result.get("y_col", ""),
        approval_id=approval_id,
        approval_tool=approval_tool,
        approval_sql=approval_sql,
        approval_explanation=approval_explanation,
    )


@app.get("/api/history/{session_id}", response_model=List[HistoryItem])
def api_history(session_id: str):
    """Get conversation history for a session."""
    if session_id not in _conversations:
        return []
    return [
        HistoryItem(
            question=h.get("question", ""),
            sql=h.get("sql", ""),
            answer=h.get("answer", ""),
        )
        for h in _conversations[session_id].history
    ]


@app.delete("/api/session/{session_id}")
def api_clear_session(session_id: str):
    """Clear a conversation session."""
    if session_id in _conversations:
        del _conversations[session_id]
    return {"status": "ok"}


@app.post("/api/approve", response_model=ApproveResponse)
def api_approve(req: ApproveRequest):
    """Approve or reject a pending write operation."""
    entry = _pending_approvals.pop(req.approval_id, None)
    if not entry:
        raise HTTPException(status_code=404, detail="Approval not found or already resolved")

    if req.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    t0 = time.perf_counter()
    approved = req.action == "approve"

    try:
        answer_text, usage = resume_after_approval(entry["pending"], approved)
        elapsed = int((time.perf_counter() - t0) * 1000)

        # Update conversation history if session exists
        session_id = entry.get("session_id", "")
        if session_id in _conversations:
            action_label = "Approved" if approved else "Rejected"
            _conversations[session_id]._history.append({
                "question": f"[{action_label} write operation]",
                "answer": answer_text[:300],
            })

        return ApproveResponse(
            approval_id=req.approval_id,
            action=req.action,
            answer=answer_text,
            elapsed_ms=elapsed,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
        )
    except Exception as e:
        return ApproveResponse(
            approval_id=req.approval_id,
            action=req.action,
            answer="",
            error=str(e),
        )


@app.get("/api/health")
def api_health():
    return {"status": "ok", "version": "0.1.0"}


# ── Helpers ─────────────────────────────────────────────

def _serialize_rows(rows: List[list]) -> List[List[Any]]:
    """Convert non-JSON-serializable values (Decimal, datetime) to primitives."""
    from decimal import Decimal
    from datetime import date, datetime

    def _conv(v: Any) -> Any:
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    return [[_conv(cell) for cell in row] for row in rows]
