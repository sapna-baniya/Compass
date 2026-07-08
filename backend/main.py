"""
main.py — FastAPI entrypoint for Compass.

Endpoints:
  POST /navigate        Run the LangGraph pipeline on a described situation.
                         Returns resources + a consent PREVIEW. Nothing is
                         stored by this call.
  POST /consent/save     Explicit, user-confirmed write to the consent ledger.
  GET  /consent/ledger/{session_id}   View everything stored for a session.
  DELETE /consent/entry/{session_id}/{entry_id}   Revoke a single saved item.
  DELETE /consent/session/{session_id}            Wipe an entire session.
"""

import uuid
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import get_graph
import consent_ledger

app = FastAPI(title="Compass API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


class NavigateRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class NavigateResponse(BaseModel):
    session_id: str
    safety_critical: bool
    handoff_message: Optional[str] = None
    extracted_needs: List[str] = []
    resources: List[dict] = []
    consent_preview: List[dict] = []


class ConsentSaveRequest(BaseModel):
    session_id: str
    resource_id: str
    resource_name: str
    retention_days: int = 30


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/navigate", response_model=NavigateResponse)
def navigate(req: NavigateRequest):
    session_id = req.session_id or str(uuid.uuid4())
    graph = get_graph()

    result = graph.invoke({
        "session_id": session_id,
        "user_message": req.message,
    })

    return NavigateResponse(
        session_id=session_id,
        safety_critical=result.get("safety_critical", False),
        handoff_message=result.get("handoff_message"),
        extracted_needs=result.get("extracted_needs", []),
        resources=result.get("prioritized_resources", []),
        consent_preview=result.get("consent_preview", []),
    )


@app.post("/consent/save")
def consent_save(req: ConsentSaveRequest):
    entry = consent_ledger.save_entry(
        session_id=req.session_id,
        resource_id=req.resource_id,
        resource_name=req.resource_name,
        retention_days=req.retention_days,
    )
    return {"saved": True, "entry": entry}


@app.get("/consent/ledger/{session_id}")
def consent_view(session_id: str):
    return {"session_id": session_id, "entries": consent_ledger.get_ledger(session_id)}


@app.delete("/consent/entry/{session_id}/{entry_id}")
def consent_revoke(session_id: str, entry_id: str):
    removed = consent_ledger.revoke_entry(session_id, entry_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"revoked": True, "entry": removed}


@app.delete("/consent/session/{session_id}")
def consent_wipe(session_id: str):
    count = consent_ledger.clear_session(session_id)
    return {"wiped": True, "entries_removed": count}
