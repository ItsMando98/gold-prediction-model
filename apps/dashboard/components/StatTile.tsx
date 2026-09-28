export function StatTile({
  label,
  value,
  meterPct,
  hint,
}: {
  label: string;
  value: string;
  meterPct?: number;
  hint?: string;
}) {
  return (
    <div className="stat-tile">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {meterPct !== undefined && (
        <div className="meter-track" role="img" aria-label={`${label}: ${meterPct.toFixed(0)}%`}>
          <div className="meter-fill" style={{ width: `${Math.max(0, Math.min(100, meterPct))}%` }} />
        </div>
      )}
      {hint && <div className="muted" style={{ fontSize: "0.72rem", marginTop: "0.4rem" }}>{hint}</div>}
    </div>
  );
}
