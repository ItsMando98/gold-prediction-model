"use client";

import { useRef, useState } from "react";
import type { Prediction } from "@/lib/api";
import { biasColorVar, formatShortDate } from "@/lib/format";

const WIDTH = 640;
const HEIGHT = 160;
const MARGIN = { top: 14, right: 12, bottom: 22, left: 12 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;

function scoreToY(score: number): number {
  return MARGIN.top + ((100 - score) / 100) * PLOT_H;
}

/** Area path clipped to one side of the 50-baseline, with exact crossing interpolation. */
function buildBandPath(
  pts: { x: number; y: number }[],
  baselineY: number,
  side: "above" | "below"
): string {
  if (pts.length === 0) return "";
  const onSide = (y: number) => (side === "above" ? y <= baselineY : y >= baselineY);
  const clampY = (y: number) => (side === "above" ? Math.min(y, baselineY) : Math.max(y, baselineY));

  const d: string[] = [`M ${pts[0].x} ${baselineY}`];
  for (let i = 0; i < pts.length; i++) {
    d.push(`L ${pts[i].x} ${clampY(pts[i].y)}`);
    if (i < pts.length - 1) {
      const a = pts[i];
      const b = pts[i + 1];
      if (onSide(a.y) !== onSide(b.y)) {
        const t = (baselineY - a.y) / (b.y - a.y);
        d.push(`L ${a.x + t * (b.x - a.x)} ${baselineY}`);
      }
    }
  }
  d.push(`L ${pts[pts.length - 1].x} ${baselineY} Z`);
  return d.join(" ");
}

export function RiskHistoryChart({ history }: { history: Prediction[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // API returns newest-first; plot chronologically left-to-right.
  const chrono = [...history].reverse();
  const step = chrono.length > 1 ? PLOT_W / (chrono.length - 1) : 0;
  const points = chrono.map((p, i) => ({
    x: MARGIN.left + i * step,
    y: scoreToY(p.risk_score),
    prediction: p,
  }));

  const baselineY = scoreToY(50);
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const bearArea = buildBandPath(points, baselineY, "above");
  const bullArea = buildBandPath(points, baselineY, "below");

  const last = points[points.length - 1];
  const hover = hoverIndex !== null ? points[hoverIndex] : null;

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!svgRef.current || points.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let bestDist = Infinity;
    points.forEach((p, i) => {
      const dist = Math.abs(p.x - svgX);
      if (dist < bestDist) {
        bestDist = dist;
        nearest = i;
      }
    });
    setHoverIndex(nearest);
  }

  return (
    <div style={{ position: "relative" }}>
      <svg
        ref={svgRef}
        className="history-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        style={{ width: "100%", height: "auto", display: "block" }}
        role="img"
        aria-label={`Risk score trend over the last ${points.length} predictions`}
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <line
          x1={MARGIN.left}
          x2={WIDTH - MARGIN.right}
          y1={baselineY}
          y2={baselineY}
          stroke="var(--baseline)"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        <path d={bearArea} fill="var(--bear)" opacity={0.1} />
        <path d={bullArea} fill="var(--bull)" opacity={0.1} />
        <path d={linePath} fill="none" stroke="var(--text-secondary)" strokeWidth={2} strokeLinejoin="round" />

        {last && (
          <circle
            cx={last.x}
            cy={last.y}
            r={5}
            fill={biasColorVar(last.prediction.bias)}
            stroke="var(--surface-1)"
            strokeWidth={2}
          />
        )}

        {hover && (
          <>
            <line
              x1={hover.x}
              x2={hover.x}
              y1={MARGIN.top}
              y2={HEIGHT - MARGIN.bottom}
              stroke="var(--grid)"
              strokeWidth={1}
            />
            <circle
              cx={hover.x}
              cy={hover.y}
              r={5}
              fill={biasColorVar(hover.prediction.bias)}
              stroke="var(--surface-1)"
              strokeWidth={2}
            />
          </>
        )}

        {points.length > 0 && (
          <>
            <text x={MARGIN.left} y={HEIGHT - 6} textAnchor="start">
              {formatShortDate(points[0].prediction.created_at)}
            </text>
            <text x={WIDTH - MARGIN.right} y={HEIGHT - 6} textAnchor="end">
              {formatShortDate(points[points.length - 1].prediction.created_at)}
            </text>
          </>
        )}
      </svg>

      {hover && (
        <div
          style={{
            position: "absolute",
            left: `${Math.min(Math.max((hover.x / WIDTH) * 100, 12), 88)}%`,
            top: 0,
            transform: "translate(-50%, -100%)",
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "0.4rem 0.6rem",
            fontSize: "0.75rem",
            whiteSpace: "nowrap",
            pointerEvents: "none",
          }}
        >
          <div style={{ fontWeight: 600 }}>{hover.prediction.risk_score.toFixed(0)} &middot; {hover.prediction.bias}</div>
          <div className="muted">{formatShortDate(hover.prediction.created_at)}</div>
        </div>
      )}
    </div>
  );
}
