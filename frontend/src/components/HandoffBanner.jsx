export default function HandoffBanner({ message }) {
  return (
    <div className="handoff-banner">
      <span className="icon">⚠</span>
      <div>
        <h3>This needs a person, not an AI</h3>
        <p>{message}</p>
        <div className="hotline">1-888-373-7888 · call or text 233733</div>
      </div>
    </div>
  )
}
