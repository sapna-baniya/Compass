import { useState } from 'react'

export default function IntakeForm({ onSubmit, loading }) {
  const [text, setText] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim()) return
    onSubmit(text.trim())
  }

  return (
    <div className="panel">
      <h2>Describe your situation</h2>
      <p className="sub">
        Write in your own words. Nothing here is saved unless you choose to save it later.
      </p>
      <form onSubmit={handleSubmit}>
        <textarea
          className="intake-textarea"
          placeholder="For example: I need help finding a safe place to stay and I'm not sure about my immigration status..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="intake-note">
          <span className="dot">●</span>
          <span>
            This box is not monitored in real time. If you are in immediate danger, call 911
            or the National Human Trafficking Hotline at 1-888-373-7888.
          </span>
        </div>
        <div className="submit-row">
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Finding resources…' : 'Find resources'}
          </button>
        </div>
      </form>
    </div>
  )
}
