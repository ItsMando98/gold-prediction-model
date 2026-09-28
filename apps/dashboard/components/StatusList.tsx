function CheckIcon() {
  return (
    <svg className="status-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" fill="var(--status-good)" opacity={0.18} />
      <path d="M5 8.3l2 2 4-4.5" stroke="var(--status-good)" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg className="status-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" fill="var(--status-critical)" opacity={0.18} />
      <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="var(--status-critical)" strokeWidth={1.6} strokeLinecap="round" />
    </svg>
  );
}

export function StatusList({ items, kind }: { items: string[]; kind: "confirmation" | "invalidation" }) {
  if (items.length === 0) return <p className="muted">None listed.</p>;
  return (
    <ul className="status-list">
      {items.map((item) => (
        <li className="status-item" key={item}>
          {kind === "confirmation" ? <CheckIcon /> : <CrossIcon />}
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
