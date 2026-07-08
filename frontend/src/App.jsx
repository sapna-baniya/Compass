import { useState, useEffect, useCallback } from 'react'
import IntakeForm from './components/IntakeForm.jsx'
import HandoffBanner from './components/HandoffBanner.jsx'
import ResourceCard from './components/ResourceCard.jsx'
import ConsentLedger from './components/ConsentLedger.jsx'

// In local dev, Vite proxies /api -> localhost:8000 (see vite.config.js).
// In production, set VITE_API_BASE to your deployed backend URL, e.g.
// https://compass-backend.onrender.com
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

function getOrCreateSessionId() {
  let id = sessionStorage.getItem('compass_session_id')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('compass_session_id', id)
  }
  return id
}

export default function App() {
  const [sessionId] = useState(getOrCreateSessionId)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [savedIds, setSavedIds] = useState(new Set())
  const [ledgerEntries, setLedgerEntries] = useState([])
  const [error, setError] = useState(null)

  const refreshLedger = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/consent/ledger/${sessionId}`)
      const data = await res.json()
      setLedgerEntries(data.entries || [])
      setSavedIds(new Set((data.entries || []).map((e) => e.resource_id)))
    } catch {
      // Ledger view failing shouldn't block the rest of the app
    }
  }, [sessionId])

  useEffect(() => { refreshLedger() }, [refreshLedger])

  async function handleIntakeSubmit(message) {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${API_BASE}/navigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
      })
      if (!res.ok) throw new Error('Request failed')
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError('Something went wrong reaching Compass. Please try again, or use the hotline below.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(resource) {
    await fetch(`${API_BASE}/consent/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        resource_id: resource.id,
        resource_name: resource.name,
      }),
    })
    refreshLedger()
  }

  async function handleRevoke(entryId) {
    await fetch(`${API_BASE}/consent/entry/${sessionId}/${entryId}`, { method: 'DELETE' })
    refreshLedger()
  }

  return (
    <div className="app-shell">
      <header className="header">
        <div>
          <div className="wordmark"><span className="mark">◈</span>Compass</div>
          <div className="tagline">Resource navigation that asks before it remembers.</div>
        </div>
        <div className="session-pill">session {sessionId.slice(0, 8)}</div>
      </header>

      <div className="layout">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <IntakeForm onSubmit={handleIntakeSubmit} loading={loading} />

          {error && (
            <div className="panel" style={{ borderColor: 'var(--critical)' }}>
              {error}
            </div>
          )}

          {result?.safety_critical && (
            <HandoffBanner message={result.handoff_message} />
          )}

          {result && !result.safety_critical && result.resources?.length > 0 && (
            <div className="panel">
              <h2>Resources for you</h2>
              <p className="sub">
                Ranked by urgency, not by us guessing what matters most to you. Save any
                that are useful — nothing else is kept.
              </p>
              <div className="resource-list">
                {result.resources.map((r) => (
                  <ResourceCard
                    key={r.id}
                    resource={r}
                    onSave={handleSave}
                    saved={savedIds.has(r.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {result && !result.safety_critical && result.resources?.length === 0 && (
            <div className="panel">
              <p>No matching resources found. Try describing your situation with more detail.</p>
            </div>
          )}
        </div>

        <ConsentLedger entries={ledgerEntries} onRevoke={handleRevoke} />
      </div>

      <div className="footer-note">
        Compass does not report to authorities, does not act on your behalf, and does not
        store anything about you without your explicit confirmation. Built for the Austin
        AI Hub Hackathon — Assist &amp; Amplify track.
      </div>
    </div>
  )
}
