import type {
  AnalysisRow,
  CompareType,
  DatasetSession,
  Metric,
  MetricAnalysis,
  PeriodAnalysis,
  PeriodOption,
  PeriodType,
  Scope,
} from "../types/dataset";
import { toNumber } from "./formatting";

/* ------------------------------------------------------------------ */
/* Filters                                                             */
/* ------------------------------------------------------------------ */

export const METRIC_LABEL: Record<Metric, string> = {
  revenue: "Revenue",
  cost: "Cost",
};

export const COMPARE_META: Record<
  CompareType,
  { short: string; long: string; unavailable: string; footnote: string }
> = {
  mom: {
    short: "MoM",
    long: "Month-on-Month",
    unavailable:
      "Month-on-Month is unavailable: it needs at least three months of data.",
    footnote: "Compares the latest three available months.",
  },
  qoq: {
    short: "QoQ",
    long: "Quarter-on-Quarter",
    unavailable:
      "Quarter-on-Quarter is unavailable: it needs two consecutive complete fiscal quarters.",
    footnote: "Only quarter pairs with complete data are listed.",
  },
  yoy: {
    short: "YoY",
    long: "Year-on-Year",
    unavailable:
      "Year-on-Year is unavailable: it needs two complete fiscal years.",
    footnote: "Only consecutive complete fiscal years are listed.",
  },
  totals: {
    short: "Totals",
    long: "Project totals",
    unavailable:
      "Totals are unavailable: no month columns were found for this metric.",
    footnote: "",
  },
};

export const COMPARE_ORDER: CompareType[] = ["mom", "qoq", "yoy", "totals"];
const DEFAULT_COMPARE_ORDER: CompareType[] = ["qoq", "mom", "yoy", "totals"];
const METRICS: Metric[] = ["revenue", "cost"];
const SCOPES: Scope[] = ["project", "region"];

export interface RawFilters {
  metric?: string | null;
  scope?: string | null;
  region?: string | null;
  compare?: string | null;
  period?: string | null;
}

export interface FilterState {
  metric: Metric;
  scope: Scope;
  region: string | null;
  compare: CompareType;
  periodId: string | null;
}

export interface Resolved {
  state: FilterState;
  analysis: MetricAnalysis | null;
  /** Only options that actually have a computed result. */
  options: PeriodOption[];
  option: PeriodOption | null;
  period: PeriodAnalysis | null;
  metricAvailable: Record<Metric, boolean>;
  scopeAvailable: Record<Scope, boolean>;
  compareAvailable: Record<CompareType, boolean>;
}

function hasData(analysis: MetricAnalysis | undefined | null): boolean {
  if (!analysis) return false;
  return Boolean(
    analysis.unique ||
      Object.keys(analysis.mom ?? {}).length ||
      Object.keys(analysis.qoq ?? {}).length ||
      Object.keys(analysis.yoy ?? {}).length,
  );
}

function isOneOf<T extends string>(
  value: string | null | undefined,
  allowed: readonly T[],
): value is T {
  return value !== null && value !== undefined && (allowed as readonly string[]).includes(value);
}

function analysisFor(
  session: DatasetSession,
  metric: Metric,
  scope: Scope,
  region: string | null,
): MetricAnalysis | null {
  if (scope === "region") {
    return region ? session.regionWise[region]?.[metric] ?? null : null;
  }
  return session.projectWise[metric] ?? null;
}

function validOptions(
  session: DatasetSession,
  analysis: MetricAnalysis | null,
  metric: Metric,
  type: PeriodType,
): PeriodOption[] {
  if (!analysis) return [];
  const results = analysis[type] ?? {};
  return (session.periods[metric]?.[type] ?? []).filter(
    (option) => results[option.id] !== undefined,
  );
}

/**
 * Turn whatever is in the URL into a fully valid filter selection.
 * Anything missing or no longer valid falls back to the best available value,
 * so the page can never end up on an option that has no data.
 */
export function resolveFilters(
  session: DatasetSession,
  raw: RawFilters,
): Resolved {
  const metricAvailable: Record<Metric, boolean> = {
    revenue: hasData(session.projectWise.revenue),
    cost: hasData(session.projectWise.cost),
  };
  const metric: Metric = isOneOf(raw.metric, METRICS) && metricAvailable[raw.metric]
    ? raw.metric
    : metricAvailable.revenue || !metricAvailable.cost
      ? "revenue"
      : "cost";

  const regionAvailable =
    Boolean(session.mapping.region_col) && session.regions.length > 0;
  const scopeAvailable: Record<Scope, boolean> = {
    project: true,
    region: regionAvailable,
  };
  const scope: Scope =
    isOneOf(raw.scope, SCOPES) && scopeAvailable[raw.scope]
      ? raw.scope
      : "project";

  const region: string | null =
    scope === "region"
      ? raw.region && session.regions.includes(raw.region)
        ? raw.region
        : session.regions[0] ?? null
      : null;

  const analysis = analysisFor(session, metric, scope, region);

  const optionsByType: Record<PeriodType, PeriodOption[]> = {
    mom: validOptions(session, analysis, metric, "mom"),
    qoq: validOptions(session, analysis, metric, "qoq"),
    yoy: validOptions(session, analysis, metric, "yoy"),
  };
  const compareAvailable: Record<CompareType, boolean> = {
    mom: optionsByType.mom.length > 0,
    qoq: optionsByType.qoq.length > 0,
    yoy: optionsByType.yoy.length > 0,
    totals: Boolean(analysis?.unique),
  };

  const compare: CompareType =
    isOneOf(raw.compare, COMPARE_ORDER) && compareAvailable[raw.compare]
      ? raw.compare
      : DEFAULT_COMPARE_ORDER.find((type) => compareAvailable[type]) ?? "totals";

  let options: PeriodOption[] = [];
  let option: PeriodOption | null = null;
  let period: PeriodAnalysis | null = null;

  if (compare !== "totals") {
    options = optionsByType[compare];
    option =
      options.find((candidate) => candidate.id === raw.period) ??
      options[options.length - 1] ??
      null;
    period = option && analysis ? analysis[compare][option.id] ?? null : null;
  }

  return {
    state: {
      metric,
      scope,
      region,
      compare,
      periodId: option?.id ?? null,
    },
    analysis,
    options,
    option,
    period,
    metricAvailable,
    scopeAvailable,
    compareAvailable,
  };
}

export function filtersToParams(state: FilterState): URLSearchParams {
  const params = new URLSearchParams();
  params.set("metric", state.metric);
  params.set("scope", state.scope);
  if (state.region) params.set("region", state.region);
  params.set("compare", state.compare);
  if (state.periodId) params.set("period", state.periodId);
  return params;
}

export function stateToRaw(state: FilterState): RawFilters {
  return {
    metric: state.metric,
    scope: state.scope,
    region: state.region,
    compare: state.compare,
    period: state.periodId,
  };
}

/* ------------------------------------------------------------------ */
/* Sentence                                                            */
/* ------------------------------------------------------------------ */

export interface SentenceParts {
  lead: string;
  primary: string;
  middle: string;
  secondary: string;
}

const SENTENCE_PATTERN =
  /^(.*?following projects -- )(.*?)( which is partially offset by (?:increase|decrease) in the following projects -- )(.*)$/s;

/**
 * Split the backend's summary sentence so project names can be emphasised.
 * The text itself is never altered; if it does not match the expected shape
 * the caller simply shows it as-is.
 */
export function splitSentence(sentence: string): SentenceParts | null {
  const match = SENTENCE_PATTERN.exec(sentence);
  if (!match) return null;
  return {
    lead: match[1],
    primary: match[2],
    middle: match[3],
    secondary: match[4],
  };
}

/* ------------------------------------------------------------------ */
/* Chart + table models                                                */
/* ------------------------------------------------------------------ */

export interface BridgeStep {
  key: string;
  label: string;
  value: number;
  kind: "total" | "delta";
}

export interface BridgeModel {
  steps: BridgeStep[];
  start: number;
  end: number;
  net: number;
}

function sumColumn(rows: AnalysisRow[], column: string): number {
  return rows.reduce((total, row) => total + toNumber(row[column]), 0);
}

/** Project name -> its change (column C) for the selected comparison. */
function changeByProject(
  period: PeriodAnalysis,
  projectCol: string,
): Map<string, number> {
  const map = new Map<string, number>();
  for (const row of period.rows) {
    map.set(String(row[projectCol]), toNumber(row.C));
  }
  return map;
}

/**
 * Variance bridge: opening total, the projects named in the summary sentence,
 * everything else grouped as "Other projects", closing total.
 */
export function buildBridge(
  period: PeriodAnalysis,
  projectCol: string,
  option: PeriodOption,
): BridgeModel | null {
  const startColumn = option.start_period;
  const endColumn = option.end_period;
  if (
    !startColumn ||
    !endColumn ||
    !period.columns.includes(startColumn) ||
    !period.columns.includes(endColumn)
  ) {
    return null;
  }

  const changes = changeByProject(period, projectCol);
  const seen = new Set<string>();

  const driverSteps = (names: string[]): BridgeStep[] =>
    names
      .filter((name) => {
        if (seen.has(name) || !changes.has(name)) return false;
        seen.add(name);
        return true;
      })
      .map((name) => ({
        key: `driver-${name}`,
        label: name,
        value: changes.get(name) ?? 0,
        kind: "delta" as const,
      }));

  const top = driverSteps(period.drivers.top);
  const bottom = driverSteps(period.drivers.bottom);

  const start = sumColumn(period.rows, startColumn);
  const end = sumColumn(period.rows, endColumn);
  const net = period.sum_to_reach;

  const driverTotal = [...top, ...bottom].reduce(
    (total, step) => total + step.value,
    0,
  );
  const others = net - driverTotal;
  const othersStep: BridgeStep[] =
    Math.abs(others) > Math.max(1e-6, Math.abs(net) * 1e-9)
      ? [{ key: "others", label: "Other projects", value: others, kind: "delta" }]
      : [];

  const deltas =
    net >= 0
      ? [...top, ...othersStep, ...bottom]
      : [...bottom, ...othersStep, ...top];

  return {
    start,
    end,
    net,
    steps: [
      { key: "start", label: startColumn, value: start, kind: "total" },
      ...deltas,
      { key: "end", label: endColumn, value: end, kind: "total" },
    ],
  };
}

export interface MoverItem {
  name: string;
  change: number;
  driver: boolean;
}

/** Biggest movers in both directions, drivers always included. */
export function buildMovers(
  period: PeriodAnalysis,
  projectCol: string,
  perSide = 5,
): MoverItem[] {
  const rows = period.rows.map((row) => ({
    name: String(row[projectCol]),
    change: toNumber(row.C),
  }));
  const sorted = [...rows].sort((a, b) => b.change - a.change);

  const drivers = new Set([...period.drivers.top, ...period.drivers.bottom]);
  const picked = new Map<string, number>();
  for (const row of [...sorted.slice(0, perSide), ...sorted.slice(-perSide)]) {
    picked.set(row.name, row.change);
  }
  for (const row of sorted) {
    if (drivers.has(row.name)) picked.set(row.name, row.change);
  }

  return [...picked.entries()]
    .map(([name, change]) => ({ name, change, driver: drivers.has(name) }))
    .sort((a, b) => b.change - a.change)
    .slice(0, 14);
}

export interface DetailRow {
  name: string;
  start: number;
  end: number;
  change: number;
  driver: boolean;
}

export function buildDetailRows(
  period: PeriodAnalysis,
  projectCol: string,
  option: PeriodOption,
): DetailRow[] {
  const startColumn = option.start_period ?? "";
  const endColumn = option.end_period ?? "";
  const drivers = new Set([...period.drivers.top, ...period.drivers.bottom]);
  return period.rows
    .map((row) => {
      const name = String(row[projectCol]);
      return {
        name,
        start: toNumber(row[startColumn]),
        end: toNumber(row[endColumn]),
        change: toNumber(row.C),
        driver: drivers.has(name),
      };
    })
    .sort((a, b) => b.change - a.change);
}

/* ------------------------------------------------------------------ */
/* Misc                                                                */
/* ------------------------------------------------------------------ */

export function scopeLabel(state: FilterState): string {
  return state.scope === "region" && state.region
    ? `Region ${state.region}`
    : "All projects";
}

export function makeExportFilename(
  workspaceName: string,
  state: FilterState,
  option: PeriodOption | null,
): string {
  const parts = [
    workspaceName,
    METRIC_LABEL[state.metric],
    state.scope === "region" && state.region ? state.region : "All projects",
    state.compare === "totals" ? "Totals" : option?.label ?? "",
  ];
  const cleaned = parts
    .filter(Boolean)
    .join(" ")
    .replace(/→/g, "to")
    .replace(/[^A-Za-z0-9._-]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return `${cleaned || "analysis"}.xlsx`;
}