import { useId } from "react";
import type { MoverItem } from "../../utils/analysisModel";
import { formatSignedUnit, unitCaption, type Unit } from "../../utils/formatting";

interface VarianceBarsProps {
  items: MoverItem[];
  unit: Unit;
}

const W = 460;
const ROW = 34;
const LABEL_W = 96;
const VALUE_W = 54;

function clip(name: string, max: number): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function VarianceBars({ items, unit }: VarianceBarsProps) {
  const titleId = useId();
  const values = items.map((item) => item.change);
  const lo = Math.min(0, ...values);
  const hi = Math.max(0, ...values);
  const span = hi - lo || 1;

  const plotWidth = W - LABEL_W - VALUE_W * 2;
  const scale = plotWidth / span;
  const zero = LABEL_W + VALUE_W + -lo * scale;
  const height = items.length * ROW + 14;

  return (
    <div className="card chart-card">
      <div className="chart-head">
        <span>Variance by project · {unitCaption(unit)}</span>
        <span className="chart-note">Solid bars drive the summary</span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${height}`}
        width="100%"
        role="img"
        aria-labelledby={titleId}
      >
        <title id={titleId}>
          Change by project for the largest increases and decreases.
        </title>
        <line className="c-axis" x1={zero} x2={zero} y1={4} y2={height - 4} />

        {items.map((item, index) => {
          const barY = 8 + index * ROW;
          const width = Math.abs(item.change) * scale;
          const x = item.change >= 0 ? zero : zero - width;
          const positive = item.change >= 0;
          return (
            <g key={item.name}>
              <text className="t-name" x={0} y={barY + 14}>
                {clip(item.name, 13)}
                <title>{item.name}</title>
              </text>
              <rect
                className={positive ? "c-up" : "c-down"}
                fillOpacity={item.driver ? 1 : 0.45}
                x={x}
                y={barY}
                width={Math.max(width, 2)}
                height={20}
                rx={3}
              />
              <text
                className="t-value"
                x={positive ? x + width + 6 : x - 6}
                y={barY + 14}
                textAnchor={positive ? "start" : "end"}
              >
                {formatSignedUnit(item.change, unit)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}