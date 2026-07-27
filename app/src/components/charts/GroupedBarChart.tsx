import { useState } from "react";

export interface GroupedBarSeries {
  key: string;
  label: string;
  color: string;
  values: (number | null)[];
}

interface Props {
  categories: string[];
  series: GroupedBarSeries[];
  height?: number;
  valueSuffix?: string;
  ariaLabel: string;
}

const MARGIN = { top: 12, right: 12, bottom: 28, left: 40 };

/** Minimal, dependency-free grouped bar chart (SVG). Built to the dataviz skill's
 * rules: fixed categorical color order, legend for multi-series, hover tooltip,
 * muted gridlines/axis, no per-bar labels. */
export default function GroupedBarChart({
  categories,
  series,
  height = 220,
  valueSuffix = "",
  ariaLabel,
}: Props) {
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);
  const width = Math.max(360, categories.length * series.length * 28 + 80);
  const plotW = width - MARGIN.left - MARGIN.right;
  const plotH = height - MARGIN.top - MARGIN.bottom;

  const allValues = series.flatMap((s) => s.values).filter((v): v is number => v != null);
  const maxValue = allValues.length ? Math.max(...allValues) : 1;
  const yScale = (v: number) => plotH - (v / maxValue) * plotH;

  const groupWidth = plotW / Math.max(1, categories.length);
  const barWidth = Math.max(4, (groupWidth * 0.7) / Math.max(1, series.length));

  const ticks = 4;
  const tickValues = Array.from({ length: ticks + 1 }, (_, i) => (maxValue / ticks) * i);

  return (
    <div style={{ overflowX: "auto", position: "relative" }}>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={ariaLabel}
        style={{ fontFamily: "var(--font)" }}
      >
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {tickValues.map((tv, i) => (
            <g key={i}>
              <line
                x1={0}
                x2={plotW}
                y1={yScale(tv)}
                y2={yScale(tv)}
                stroke="var(--border)"
                strokeWidth={1}
              />
              <text x={-8} y={yScale(tv)} dy={4} textAnchor="end" fontSize={10} fill="var(--text-faint)">
                {Math.round(tv)}
              </text>
            </g>
          ))}
          <line x1={0} x2={0} y1={0} y2={plotH} stroke="var(--text-faint)" strokeWidth={1} />
          <line x1={0} x2={plotW} y1={plotH} y2={plotH} stroke="var(--text-faint)" strokeWidth={1} />

          {categories.map((cat, ci) => (
            <g key={cat} transform={`translate(${ci * groupWidth},0)`}>
              {series.map((s, si) => {
                const v = s.values[ci];
                if (v == null) return null;
                const barH = plotH - yScale(v);
                const x = groupWidth / 2 - (barWidth * series.length) / 2 + si * barWidth;
                return (
                  <rect
                    key={s.key}
                    x={x}
                    y={yScale(v)}
                    width={barWidth - 2}
                    height={Math.max(0, barH)}
                    rx={2}
                    fill={s.color}
                    onMouseEnter={(e) =>
                      setHover({
                        x: e.nativeEvent.offsetX,
                        y: e.nativeEvent.offsetY,
                        text: `${s.label} · ${cat}: ${v}${valueSuffix}`,
                      })
                    }
                    onMouseLeave={() => setHover(null)}
                  />
                );
              })}
              <text
                x={groupWidth / 2}
                y={plotH + 16}
                textAnchor="middle"
                fontSize={10}
                fill="var(--text-faint)"
              >
                {cat}
              </text>
            </g>
          ))}
        </g>
      </svg>
      {hover && (
        <div
          style={{
            position: "absolute",
            left: hover.x + 12,
            top: hover.y,
            background: "var(--text)",
            color: "var(--bg)",
            padding: "2px 8px",
            borderRadius: 4,
            fontSize: 12,
            pointerEvents: "none",
            whiteSpace: "nowrap",
          }}
        >
          {hover.text}
        </div>
      )}
      {series.length > 1 && (
        <div style={{ display: "flex", gap: "1rem", marginTop: 4, flexWrap: "wrap" }}>
          {series.map((s) => (
            <span key={s.key} style={{ fontSize: 12, color: "var(--text-muted)" }}>
              <span
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background: s.color,
                  marginRight: 4,
                }}
              />
              {s.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
