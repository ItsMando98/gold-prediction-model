import { getCurrentPrediction } from "@/lib/api";

function biasClass(bias: string) {
  if (bias === "bearish") return "bias-bearish";
  if (bias === "bullish") return "bias-bullish";
  return "bias-neutral";
}

export default async function OverviewPage() {
  const prediction = await getCurrentPrediction();

  return (
    <>
      <h1>Gold Prediction Model</h1>
      <p className="muted">XAUUSD &middot; Friday close &rarr; Monday baseline</p>

      {!prediction && (
        <div className="card">
          <p>No prediction available yet.</p>
          <p className="muted">
            Run the worker&apos;s weekly job (or <code>python -m apps.worker.jobs</code>) once
            historical data has been backfilled.
          </p>
        </div>
      )}

      {prediction && (
        <>
          <div className="card">
            <p className="muted">Gold Risk Score (0 = strongly bullish, 100 = strongly bearish)</p>
            <p className={`score ${biasClass(prediction.bias)}`}>
              {prediction.risk_score.toFixed(0)}
            </p>
            <p className={biasClass(prediction.bias)}>{prediction.bias.toUpperCase()}</p>
            <p className="muted">
              Regime: <strong>{prediction.regime}</strong> &middot; Confidence:{" "}
              {(prediction.confidence * 100).toFixed(0)}%{" "}
              {prediction.model_versions?.calibrated === false && (
                <span title="Not yet backed by a historical calibration run">(uncalibrated)</span>
              )}
            </p>
            <p className="muted">
              Horizon: {prediction.horizon} &middot; Target: {new Date(prediction.target_time).toUTCString()}
            </p>
          </div>

          <div className="card">
            <h2>Drivers</h2>
            <table>
              <thead>
                <tr>
                  <th>Component</th>
                  <th>Contribution</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {prediction.drivers
                  .slice()
                  .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
                  .map((d) => (
                    <tr key={d.name}>
                      <td>{d.name}</td>
                      <td>{d.contribution > 0 ? "+" : ""}{d.contribution.toFixed(1)}</td>
                      <td className="muted">{d.description}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2>Key Levels</h2>
            <p>Support: {prediction.key_levels.support?.join(", ") ?? "-"}</p>
            <p>Resistance: {prediction.key_levels.resistance?.join(", ") ?? "-"}</p>
          </div>

          <div className="card">
            <h2>Confirmation</h2>
            <ul>
              {prediction.confirmations.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>

          <div className="card">
            <h2>Invalidation</h2>
            <ul>
              {prediction.invalidation.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>

          {prediction.contradictions.length > 0 && (
            <div className="card">
              <h2>Contradicting Signals</h2>
              <ul>
                {prediction.contradictions.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </>
  );
}
