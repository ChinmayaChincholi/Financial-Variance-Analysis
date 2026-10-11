import { useId } from "react";
import type { BridgeModel } from "../../utils/analysisModel";
import {
  formatSignedUnit,
  formatUnit,
  unitCaption,
  type Unit,
} from "../../utils/formatting";

interface BridgeChartProps {
  model: BridgeModel;
  unit: Unit;
}

const W = 640;
const H = 270;
const PAD_TOP = 28;
const PAD_BOTTOM = 52;
const PAD_X = 6;

function niceStep(range: number): number {
  const magnitude = 10 ** Math.floor(Math.log10(range || 1));
  const normalized = range / magnitude;
  if (normalized <= 2) return magnitude / 2;
  if (normalized <= 5) return magnitude;
  return magnitude * 2;
}

function wrapLabel(label: string, maxChars: number): string[] {
  const words = label.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxChars || !current) {
      current = next;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);

  const clipped = lines.slice(0, 2).map((line) =>
    line.length > maxChars ? `${line.slice(0, maxChars - 1)}…` : line,
  );
  if (lines.length > 2) {
    clipped[1] = `${clipped[1].replace(/…$/, "").slice(0, maxChars - 1)}…`;
  }
  return clipped;
}

interface Bar {
  key: string;
  label: string;
  kind: "total" | "delta";
  value: number;
  from: number;
  to: number;
}

export function BridgeChart({ model, unit }: BridgeChartProps) {
  const titleId = useId();

  // Walk the running level so every delta bar floats from where the last
  // one ended, like a standard financial bridge.
  let level = model.start;
  const bars: Bar[] = model.steps.map((step) => {
    if (step.kind === "total") {
      level = step.value;
      return { ...step, from: 0, to: step.value };
    }
    const from = level;
    level += step.value;
    return { ...step, from, to: level };
  });

  const levels = bars.flatMap((bar) =>
    bar.kind === "total" ? [bar.value] : [bar.from, bar.to],
  );
  const minLevel = Math.min(...levels);
  const maxLevel = Math.max(...levels);
  const range = maxLevel - minLevel || Math.abs(maxLevel) * 0.1 || 1;

  let lo: number;
  if (minLevel > 0) {
    const step = niceStep(range);
    lo = Math.max(0, Math.floor((minLevel - range * 0.6) / step) * step);
  } else {
    lo = minLevel - range * 0.12;
  }
  const hi = maxLevel + range * 0.1;
  const axisBroken = lo > 0;

  const plotHeight = H - PAD_TOP - PAD_BOTTOM;
  const y = (value: number) => PAD_TOP + ((hi - value) / (hi - lo)) * plotHeight;

  const slot = (W - PAD_X * 2) / bars.length;
  const barWidth = Math.min(slot * 0.62, 64);
  const maxChars = Math.max(6, Math.floor(slot / 6.6));

  const first = model.steps[0];
  const last = model.steps[model.steps.length - 1];
  const description = `Variance bridge from ${first.label} ${formatUnit(
    model.start,
    unit,
  )} to ${last.label} ${formatUnit(model.end, unit)}, a change of ${formatSignedUnit(
    model.net,
    unit,
  )}.`;

  return (
    <div className="card chart-card">
      <div className="chart-head">
        <span>Variance bridge · {unitCaption(unit)}</span>
        {axisBroken && (
          <span className="chart-note">
            Axis starts at {formatUnit(lo, unit)}
          </span>
        )}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-labelledby={titleId}
      >
        <title id={titleId}>{description}</title>

        {bars.map((bar, index) => {
          const x = PAD_X + index * slot + (slot - barWidth) / 2;
          const top = y(Math.max(bar.from, bar.to));
          const bottom = bar.kind === "total" ? y(lo) : y(Math.min(bar.from, bar.to));
          const height = Math.max(2, bottom - top);
          const className =
            bar.kind === "total"
              ? "c-total"
              : bar.value >= 0
                ? "c-up"
                : "c-down";
          const label =
            bar.kind === "total"
              ? formatUnit(bar.value, unit)
              : formatSignedUnit(bar.value, unit);
          const lines = wrapLabel(bar.label, maxChars);
          const next = bars[index + 1];

          return (
            <g key={bar.key}>
              {next && (
                <line
                  className="c-link"
                  x1={x + barWidth}
                  x2={x + slot}
                  y1={y(bar.to)}
                  y2={y(bar.to)}
                />
              )}
              <rect
                className={className}
                x={x}
                y={top}
                width={barWidth}
                height={height}
                rx={3}
              />
              <text
                className="t-value"
                x={x + barWidth / 2}
                y={top - 6}
                textAnchor="middle"
              >
                {label}
              </text>
              <text
                className="t-label"
                x={x + barWidth / 2}
                y={H - PAD_BOTTOM + 18}
                textAnchor="middle"
              >
                {lines.map((line, lineIndex) => (
                  <tspan
                    key={lineIndex}
                    x={x + barWidth / 2}
                    dy={lineIndex === 0 ? 0 : 14}
                  >
                    {line}
                  </tspan>
                ))}
                <title>{bar.label}</title>
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}