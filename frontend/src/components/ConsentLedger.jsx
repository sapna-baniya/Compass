function formatTime(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function ConsentLedger({ entries, onRevoke }) {
  return (
    <div className="panel logbook">
      <h2>Your logbook</h2>
      <p className="sub">
        Everything stored here, and only here — visible to you, deletable by you.
      </p>

      {entries.length === 0 ? (
        <div className="logbook-empty">
          Nothing saved yet. Resources only appear here when you choose to save them.
        </div>
      ) : (
        <div className="logbook-entries">
          {entries.map((entry) => (
            <div className="logbook-entry" key={entry.entry_id}>
              <div className="logbook-stamp">✓</div>
              <div className="logbook-entry-body">
                <div className="logbook-entry-name">{entry.resource_name}</div>
                <div className="logbook-entry-meta">
                  saved {formatTime(entry.saved_at)} · expires {formatTime(entry.expires_at)}
                </div>
                <button className="logbook-revoke" onClick={() => onRevoke(entry.entry_id)}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="consent-preview-note">
        Saved items auto-expire after 30 days unless you save them again. You can remove
        any entry immediately, at any time, for any reason.
      </div>
    </div>
  )
}
