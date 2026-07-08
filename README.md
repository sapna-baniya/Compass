# Compass

**Resource navigation that asks before it remembers.**

Built for the Austin AI Hub Hackathon — Assist & Amplify track.

Compass helps trafficking survivors and frontline case workers find legal, medical,
immigration, and shelter resources — without storing anything about the user unless
they explicitly say so.

## Why this design

Most support tools either over-collect data or make decisions that should stay with a
human. Compass is built so that:

- **Nothing persists by default.** Every `/navigate` call is stateless from a storage
  perspective — it returns resources and a *preview* of what could be saved, but writes
  nothing.
- **Saving is a separate, explicit action.** Only `POST /consent/save` writes to the
  consent ledger, and only because the user clicked "Save to my logbook."
- **Prioritization is rule-based, not model-based.** Ranking resources by urgency is a
  safety-relevant decision — it should be deterministic and auditable, not a language
  model's best guess.
- **Safety-critical messages never reach retrieval or storage.** The Safety Router in
  the LangGraph pipeline intercepts anything indicating immediate danger and routes
  straight to a real hotline, before any other agent runs.

## Architecture

```
frontend/  React + Vite app. IntakeForm -> ResourceCard list -> ConsentLedger ("logbook")
backend/
  main.py           FastAPI routes
  agents.py         LangGraph pipeline: intake -> safety router -> retrieval ->
                     prioritization -> consent preview  (or -> handoff, and stop)
  rag.py            FAISS + sentence-transformers retrieval over the resource KB
  consent_ledger.py Explicit, auditable consent store (in-memory for the demo)
  data/resources.json  Seed knowledge base — public hotline/legal-aid/shelter data only
```

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then add your free Groq API key
uvicorn main:app --reload --port 8000
```

Get a free Groq API key at https://console.groq.com/keys — Llama 3.3 on Groq's free
tier is plenty for the demo. If you skip the key entirely, the intake agent falls back
to simple keyword extraction so the pipeline still runs end-to-end.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173. The Vite dev server proxies `/api/*` to the FastAPI
backend on port 8000.

## Demo script (for your ≤3 minute video)

1. Type a situation into the intake box (e.g. "I need help finding a safe place to stay
   and I'm not sure about my immigration status") → show ranked resources appear.
2. Click "Save to my logbook" on one resource → show it appear in the logbook sidebar
   with a visible timestamp and expiry.
3. Click "Remove" on that entry → show it disappear immediately.
4. Type something indicating immediate danger (e.g. "he's here right now, I can't
   leave") → show the Handoff Agent intercept it and display the hotline banner
   instead of resources.
5. Briefly show `agents.py` to narrate the graph: intake → safety router → (retrieval →
   prioritization → consent preview) OR (handoff, full stop).

## Ethics / guideline compliance notes

- No facial recognition, biometric data, or re-identification of any kind — the
  knowledge base is text-only, public resource data (hotlines, legal aid directories,
  federal program pages), not scraped survivor or victim data.
- Model provider: Groq (Llama 3.3). Disclosed here and should be restated in your
  submission's "AI model use" section.
- No content in this project is AI-generated media depicting real people or events, so
  no labelling requirement applies beyond this disclosure.

## Team

Sai (Venkata Sai Kumar Erla) & Nista Sunuwar
