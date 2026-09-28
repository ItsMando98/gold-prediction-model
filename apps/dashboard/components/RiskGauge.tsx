import { biasClass } from "@/lib/format";

export function RiskGauge({ score, bias }: { score: number; bias: string }) {
  const clamped = Math.max(0, Math.min(100, score));

  return (
    <div>
      <div className="hero-top">
        <span className="hero-figure" aria-label={`Gold risk score ${clamped.toFixed(0)} of 100`}>
          {clamped.toFixed(0)}
        </span>
        <span className={`bias-pill ${biasClass(bias)}`}>
          <span className="dot" aria-hidden="true" />
          {bias}
        </span>
      </div>

      <div className="gauge" role="img" aria-label={`Score ${clamped.toFixed(0)} of 100, ${bias}`}>
        <div className="gauge-track">
          <div className="gauge-pointer" style={{ left: `${clamped}%` }} />
        </div>
        <div className="gauge-scale">
          <span>0 &middot; strongly bullish</span>
          <span>50 &middot; neutral</span>
          <span>100 &middot; strongly bearish</span>
        </div>
      </div>
    </div>
  );
}
