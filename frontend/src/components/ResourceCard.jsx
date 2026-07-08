const URGENCY_LABEL = {
  critical: 'Urgent',
  high: 'High priority',
  medium: 'Medium priority',
  low: 'Lower priority',
}

export default function ResourceCard({ resource, onSave, saved }) {
  const urgencyClass = `urgency-badge urgency-${resource.urgency}`

  return (
    <div className="resource-card">
      <div className="top-row">
        <h3>{resource.name}</h3>
        <span className={urgencyClass}>{URGENCY_LABEL[resource.urgency] || resource.urgency}</span>
      </div>
      <p className="desc">{resource.description}</p>
      <div className="meta">{resource.contact}</div>
      <div className="actions">
        <a href={resource.url} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>
          Learn more →
        </a>
        <button
          className="btn-save"
          disabled={saved}
          onClick={() => onSave(resource)}
        >
          {saved ? 'Saved to logbook ✓' : 'Save to my logbook'}
        </button>
      </div>
    </div>
  )
}
