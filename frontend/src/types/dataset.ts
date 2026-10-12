export type Scope = "project" | "region";
export type Metric = "revenue" | "cost";
export type PeriodType = "mom" | "qoq" | "yoy";
export type CompareType = PeriodType;

export interface ColumnMapping {
  project_col: string;
  region_col: string | null;
  revenue_month_year_cols: string[];
  cost_month_year_cols: string[];
}

export interface ClarificationCandidate {
  column: string;
  score: number;
  reasons: string[];
  sample_values: unknown[];
}

export interface ClarificationRequest {
  field: string;
  message: string;
  candidates: ClarificationCandidate[];
  allow_none?: boolean;
}

export interface PeriodOption {
  id: string;
  label: string;
  /** Name of the comparison-view column holding the earlier period total. */
  start_period?: string;
  /** Name of the comparison-view column holding the later period total. */
  end_period?: string;
  /** Month columns belonging to each period (used to highlight the trend). */
  start_months?: string[];
  end_months?: string[];
}

export interface AnalysisRow {
  [key: string]: string | number | null | undefined;
}

export interface TableResult {
  rows: AnalysisRow[];
  columns: string[];
}

export interface DriverSelection {
  top: string[];
  bottom: string[];
}

export interface PeriodAnalysis extends TableResult {
  sum_to_reach: number;
  summary_sentence: string;
  drivers: DriverSelection;
}

export interface MetricAnalysis {
  unique: TableResult | null;
  mom: Record<string, PeriodAnalysis>;
  qoq: Record<string, PeriodAnalysis>;
  yoy: Record<string, PeriodAnalysis>;
}

export interface MetricPeriods {
  mom: PeriodOption[];
  qoq: PeriodOption[];
  yoy: PeriodOption[];
}

export type CurrencySource = "headers" | "values" | "both" | "assumed";

export interface CurrencyInfo {
  /** ISO code, or null when several currencies were found. */
  code: string | null;
  /** Display symbol; empty when currencies are mixed. */
  symbol: string;
  name: string;
  /** False when nothing was found and dollars were assumed. */
  detected: boolean;
  mixed: boolean;
  found: string[];
  source: CurrencySource;
}

export interface TrendSeries {
  months: string[];
  values: number[];
}

export type MetricTrend = Record<Metric, TrendSeries | null>;

export interface TrendData {
  project: MetricTrend;
  regions: Record<string, MetricTrend>;
}

export interface DatasetSummary {
  unique_projects: number;
  row_count: number;
  column_count: number;
  regions: string[];
  first_month: string | null;
  last_month: string | null;
  month_count: number;
  metrics: Metric[];
  comparisons: Record<PeriodType, number>;
  /** Absent on workspaces saved before currency detection existed. */
  currency?: CurrencyInfo;
}

export interface DatasetMetadata {
  filename: string;
  sheet_name: string;
  row_count: number;
  column_count: number;
}

export interface DatasetSession {
  dataset: DatasetMetadata;
  mapping: ColumnMapping;
  regions: string[];
  periods: Record<Metric, MetricPeriods>;
  projectWise: Record<Metric, MetricAnalysis>;
  regionWise: Record<string, Record<Metric, MetricAnalysis>>;
  summary: DatasetSummary;
  /** Absent on workspaces saved before the monthly trend existed. */
  trend?: TrendData;
  version?: number;
}

export interface WorkspaceMeta {
  id: string;
  name: string;
  filename: string;
  sheet_name: string;
  file_size: number | null;
  created_at: string;
  last_opened_at: string;
  summary: DatasetSummary;
}

export interface WorkspaceDetail {
  meta: WorkspaceMeta;
  session: DatasetSession;
}

export type IngestionStatus =
  | "resolved"
  | "needs_clarification"
  | "needs_sheet_selection";

export interface IngestionResponse {
  status: IngestionStatus;
  workspace?: WorkspaceMeta;
  clarifications?: ClarificationRequest[];
  sheets?: string[];
  filename?: string;
  sheet_name?: string;
  header_row_index?: number | null;
  header_row_confidence?: number | null;
}

/*
 * Real processing-stream events. The backend never sends fake percentage
 * progress, only genuine stage transitions (plus optional detail text).
 */
export interface DatasetProgressEvent {
  type: "progress";
  stage: string;
  detail?: string;
}

export interface DatasetResultEvent {
  type: "result";
  data: IngestionResponse;
}

export interface DatasetErrorEvent {
  type: "error";
  message: string;
}

export type DatasetStreamEvent =
  | DatasetProgressEvent
  | DatasetResultEvent
  | DatasetErrorEvent;