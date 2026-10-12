import { useId } from "react";
import type { CurrencyInfo } from "../../types/dataset";
import type { TrendModel } from "../../utils/analysisModel";
import {
  formatCompactMoney,
  formatMoney,
  scaleCaption,
} from "../../utils/formatting";

interface TrendChartProps {
  model: TrendModel;
  currency: CurrencyInfo;
}

const W = 520;
const H = 270;
const PAD_LEFT = 62;
const PAD_RIGHT = 8;
const PAD_TOP = 14;
const TICKS = 4;

function niceCeil(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const normalized = value / magnitude;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

export function TrendChart({ model, currency }: TrendChartProps) {
  const titleId = useId();
  const { bars } = model;

  const maxValue = Math.max(0, ...bars.map((bar) => bar.value));
  const minValue = Math.min(0, ...bars.map((bar) => bar.value));
  const top = maxValue > 0 ? niceCeil(maxValue / TICKS) * TICKS : 0;
  const bottom = minValue < 0 ? -niceCeil(-minValue / TICKS) * TICKS : 0;
  const span = top - bottom || 1;

  const rotate = bars.length > 8;
  const padBottom = rotate ? 58 : 34;
  const plotHeight = H - PAD_TOP - padBottom;
  const plotWidth = W - PAD_LEFT - PAD_RIGHT;
  const y = (value: number) => PAD_TOP + ((top - value) / span) * plotHeight;
  const zeroY = y(0);

  const slot = plotWidth / bars.length;
  const barWidth = Math.max(3, Math.min(slot * 0.7, 36));
  const labelStep = bars.length > 24 ? Math.ceil(bars.length / 24) : 1;

  const ticks = Array.from({ length: TICKS + 1 }, (_, index) =>
    bottom + (span / TICKS) * index,
  );

  const description = `Monthly total from ${bars[0].month} to ${
    bars[bars.length - 1].month
  }. ${model.startLabel} and ${model.endLabel} are highlighted.`;

  return (
    <div className="card chart-card">
      <div className="chart-head">
        <span>Monthly trend · {scaleCaption(currency)}</span>
      </div>

      <div className="legend" aria-hidden="true">
        <span>
          <i className="swatch t-start" />
          {model.startLabel}
        </span>
        <span>
          <i className="swatch t-end" />
          {model.endLabel}
        </span>
        <span>
          <i className="swatch t-other" />
          Other months
        </span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-labelledby={titleId}
      >
        <title id={titleId}>{description}</title>

        {ticks.map((tick) => (
          <g key={tick}>
            <line
              className="c-grid"
              x1={PAD_LEFT}
              x2={W - PAD_RIGHT}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text
              className="t-label"
              x={PAD_LEFT - 8}
              y={y(tick) + 4}
              textAnchor="end"
            >
              {formatCompactMoney(tick, currency)}
            </text>
          </g>
        ))}
        <line
          className="c-axis"
          x1={PAD_LEFT}
          x2={W - PAD_RIGHT}
          y1={zeroY}
          y2={zeroY}
        />

        {bars.map((bar, index) => {
          const x = PAD_LEFT + index * slot + (slot - barWidth) / 2;
          const barTop = y(Math.max(bar.value, 0));
          const barBottom = y(Math.min(bar.value, 0));
          const height = Math.max(1.5, barBottom - barTop);
          const cx = x + barWidth / 2;
          const labelY = H - padBottom + 16;
          const showLabel = index % labelStep === 0;

          return (
            <g key={bar.month}>
              <rect
                className={`t-bar t-${bar.role}`}
                x={x}
                y={barTop}
                width={barWidth}
                height={height}
                rx={2}
              >
                <title>{`${bar.month}: ${formatMoney(bar.value, currency)}`}</title>
              </rect>
              {showLabel && (
                <text
                  className="t-label"
                  x={cx}
                  y={labelY}
                  textAnchor={rotate ? "end" : "middle"}
                  transform={rotate ? `rotate(-45 ${cx} ${labelY})` : undefined}
                >
                  {bar.month}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}