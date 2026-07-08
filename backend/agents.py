"""
agents.py — Compass's LangGraph multi-agent pipeline.

Flow:
  Intake Agent
       |
  Safety Router  --(safety-critical)--> Handoff Agent (STOP, no retrieval/storage)
       |
  (not critical)
       |
  Retrieval Agent (RAG over public resource index)
       |
  Prioritization Agent (rule-based, not LLM — safety-critical ranking
                         should not depend on model output)
       |
  Consent Preview Agent (prepares what COULD be saved; nothing is written
                          to the consent ledger until the user explicitly
                          confirms via the /consent/save endpoint)

Design principle: nothing in this graph persists survivor data. The graph
operates on an ephemeral in-memory state per request. Only an explicit,
separate API call (see main.py: POST /consent/save) writes anything to
the consent ledger, and every write is itself logged with what/why/duration.
"""

import os
import json
from typing import TypedDict, List, Dict, Optional

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from rag import get_resource_index

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SAFETY_CRITICAL_KEYWORDS = [
    "in danger", "right now", "trafficker is here", "being held",
    "can't leave", "cant leave", "locked in", "emergency", "hurt me",
    "going to hurt", "immediate danger", "help now", "police",
]


class CompassState(TypedDict, total=False):
    session_id: str
    user_message: str
    jurisdiction: Optional[str]
    extracted_needs: List[str]
    safety_critical: bool
    retrieved_resources: List[Dict]
    prioritized_resources: List[Dict]
    consent_preview: List[Dict]
    handoff_message: Optional[str]


def _get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return ChatGroq(model=GROQ_MODEL, api_key=api_key, temperature=0)


# ---------------------------------------------------------------------------
# Agent nodes
# ---------------------------------------------------------------------------

def intake_agent(state: CompassState) -> CompassState:
    """Extracts structured needs and jurisdiction from the user's free-text
    description. Falls back to simple keyword extraction if no LLM key is
    configured, so the pipeline still runs end-to-end without a key."""
    message = state["user_message"]
    llm = _get_llm()

    lowered = message.lower()
    safety_critical = any(kw in lowered for kw in SAFETY_CRITICAL_KEYWORDS)

    if llm:
        prompt = (
            "You are the intake step of a survivor-support resource navigator. "
            "Given the user's message, extract ONLY structured data. "
            "Return strict JSON with keys: "
            "needs (array from: immediate_safety, shelter, legal, immigration, "
            "medical, counseling, reporting, referral, case_management, know_your_rights), "
            "jurisdiction (US state code if mentioned, else null), "
            "safety_critical (boolean, true only if the user indicates they are in "
            "immediate physical danger right now).\n\n"
            f"User message: {message}\n\nJSON:"
        )
        try:
            resp = llm.invoke(prompt)
            parsed = json.loads(resp.content)
            state["extracted_needs"] = parsed.get("needs", ["referral"])
            state["jurisdiction"] = parsed.get("jurisdiction")
            state["safety_critical"] = bool(parsed.get("safety_critical")) or safety_critical
        except Exception:
            state["extracted_needs"] = ["referral"]
            state["jurisdiction"] = None
            state["safety_critical"] = safety_critical
    else:
        # No API key configured — degrade gracefully to keyword matching
        needs = []
        if any(w in lowered for w in ["shelter", "housing", "stay"]):
            needs.append("shelter")
        if any(w in lowered for w in ["visa", "immigration", "status", "papers"]):
            needs.append("immigration")
        if any(w in lowered for w in ["lawyer", "legal", "court"]):
            needs.append("legal")
        if any(w in lowered for w in ["doctor", "medical", "health", "hospital"]):
            needs.append("medical")
        if not needs:
            needs = ["referral"]
        state["extracted_needs"] = needs
        state["jurisdiction"] = None
        state["safety_critical"] = safety_critical

    return state


def safety_router(state: CompassState) -> str:
    return "handoff" if state.get("safety_critical") else "retrieval"


def handoff_agent(state: CompassState) -> CompassState:
    """Safety-critical requests never reach the LLM-driven retrieval/
    prioritization steps. The system stops and routes to a real hotline."""
    state["handoff_message"] = (
        "This looks like it may be an urgent safety situation. Compass does not "
        "handle emergencies. Please contact the National Human Trafficking Hotline "
        "at 1-888-373-7888 (call or text 233733), available 24/7, or call 911 if you "
        "are in immediate danger."
    )
    state["retrieved_resources"] = []
    state["prioritized_resources"] = []
    state["consent_preview"] = []
    return state


def retrieval_agent(state: CompassState) -> CompassState:
    index = get_resource_index()
    query = " ".join(state.get("extracted_needs", ["referral"])) + " " + state["user_message"]
    results = index.search(query, jurisdiction=state.get("jurisdiction"), top_k=6)
    state["retrieved_resources"] = results
    return state


def prioritization_agent(state: CompassState) -> CompassState:
    """Rule-based ranking — deliberately NOT delegated to the LLM. Urgency
    ordering for a survivor population is a safety-relevant decision and
    should be deterministic and auditable, not a model's best guess."""
    resources = state.get("retrieved_resources", [])
    ranked = sorted(
        resources,
        key=lambda r: (URGENCY_ORDER.get(r.get("urgency", "low"), 3), -r.get("relevance_score", 0)),
    )
    state["prioritized_resources"] = ranked
    return state


def consent_preview_agent(state: CompassState) -> CompassState:
    """Builds a preview of what COULD be saved to the consent ledger for
    each resource the user engages with. Nothing here is persisted — it is
    only returned to the frontend so the user can review before opting in."""
    preview = []
    for r in state.get("prioritized_resources", []):
        preview.append({
            "resource_id": r["id"],
            "resource_name": r["name"],
            "what_would_be_stored": f"Reference to resource '{r['name']}' and the need category it addresses.",
            "why": "So you can find this resource again later without re-describing your situation.",
            "default_retention": "Not stored unless you confirm.",
        })
    state["consent_preview"] = preview
    return state


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(CompassState)

    graph.add_node("intake", intake_agent)
    graph.add_node("handoff", handoff_agent)
    graph.add_node("retrieval", retrieval_agent)
    graph.add_node("prioritization", prioritization_agent)
    graph.add_node("consent_preview", consent_preview_agent)

    graph.set_entry_point("intake")
    graph.add_conditional_edges("intake", safety_router, {
        "handoff": "handoff",
        "retrieval": "retrieval",
    })
    graph.add_edge("handoff", END)
    graph.add_edge("retrieval", "prioritization")
    graph.add_edge("prioritization", "consent_preview")
    graph.add_edge("consent_preview", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
