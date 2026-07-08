"""
consent_ledger.py — The explicit, auditable consent store.

This is the only place in Compass where anything about a survivor's
session can persist beyond the request/response cycle, and it only
happens when the frontend calls save_entry() in direct response to a
user clicking "Save this" — never automatically.

For the hackathon demo this uses an in-memory dict keyed by session_id.
In a real deployment this would be swapped for an encrypted, access-
controlled store with per-entry expiry enforcement, but the API shape
(explicit write, visible log, revocable) stays the same.
"""

import uuid
import datetime
from typing import Dict, List, Optional

# session_id -> list of ledger entries
_LEDGER: Dict[str, List[Dict]] = {}


def save_entry(session_id: str, resource_id: str, resource_name: str,
               retention_days: int = 30) -> Dict:
    entry = {
        "entry_id": str(uuid.uuid4()),
        "resource_id": resource_id,
        "resource_name": resource_name,
        "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
        "retention_days": retention_days,
        "expires_at": (
            datetime.datetime.utcnow() + datetime.timedelta(days=retention_days)
        ).isoformat() + "Z",
        "consent_confirmed": True,
    }
    _LEDGER.setdefault(session_id, []).append(entry)
    return entry


def get_ledger(session_id: str) -> List[Dict]:
    return _LEDGER.get(session_id, [])


def revoke_entry(session_id: str, entry_id: str) -> Optional[Dict]:
    entries = _LEDGER.get(session_id, [])
    for e in entries:
        if e["entry_id"] == entry_id:
            entries.remove(e)
            return e
    return None


def clear_session(session_id: str) -> int:
    """Wipes all consent-ledger entries for a session (e.g. user ends
    session / requests full deletion). Returns count of entries removed."""
    count = len(_LEDGER.get(session_id, []))
    _LEDGER.pop(session_id, None)
    return count
