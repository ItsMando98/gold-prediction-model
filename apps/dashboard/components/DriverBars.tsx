"use client";

import { useState } from "react";
import type { PredictionDriver } from "@/lib/api";

export function DriverBars({ drivers }: { drivers: PredictionDriver[] }) {
  const [showTable, setShowTable] = useState(false);

  const sorted = [...drivers].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const maxAbs = Math.max(1, ...sorted.map((d) => Math.abs(d.contribution)));

  return (
    <div className="card">
      <div className="card-header-row">
        <h2>Drivers</h2>
        <button
          className="toggle-btn"
          onClick={() => setShowTable((v) => !v)}
          aria-pressed={showTable}
        >
          {showTable ? "Show chart" : "Show table"}
        </button>
      </div>

      {!showTable && (
        <>
          <div className="legend">
            <span className="legend-item">
              <span className="legend-swatch" style={{ background: "var(--bull)" }} />
              Bullish pull
            </span>
            <span className="legend-item">
              <span className="legend-swatch" style={{ background: "var(--bear)" }} />
              Bearish pull
            </span>
            <span className="legend-item">
              <span className="legend-swatch" style={{ background: "var(--neutral)" }} />
              No data
            </span>
          </div>

          <div>
            {sorted.map((d) => {
              const unavailable = d.description === "no data available";
              const pct = (Math.abs(d.contribution) / maxAbs) * 50;
              const isBear = d.contribution > 0;
              const color = unavailable ? "var(--neutral)" : isBear ? "var(--bear)" : "var(--bull)";

              return (
                <div key={d.name} className={`driver-row${unavailable ? " driver-unavailable" : ""}`}>
                  <span className="driver-name">{d.name.replace(/_/g, " ")}</span>
                  <div className="driver-track" title={d.description ?? undefined}>
                    <div className="center-line" />
                    <div
                      className="driver-bar"
                      style={{
                        background: color,
                        width: `${Math.max(pct, unavailable ? 0 : 1.5)}%`,
                        left: isBear || unavailable ? "50%" : `${50 - pct}%`,
                      }}
                    />
                  </div>
                  <span className="driver-value">
                    {unavailable ? "n/a" : `${d.contribution > 0 ? "+" : ""}${d.contribution.toFixed(1)}`}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}

      {showTable && (
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Contribution</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((d) => (
              <tr key={d.name}>
                <td style={{ textTransform: "capitalize" }}>{d.name.replace(/_/g, " ")}</td>
                <td>
                  {d.contribution > 0 ? "+" : ""}
                  {d.contribution.toFixed(1)}
                </td>
                <td className="muted">{d.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
