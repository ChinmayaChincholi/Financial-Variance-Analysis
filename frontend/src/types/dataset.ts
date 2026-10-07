export type Scope = "project" | "region";

export type Metric = "revenue" | "cost";

export type PeriodType = "MoM" | "QoQ" | "YoY";

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

export interface DatasetMetadata {
  filename: string;
  sheet_name: string;
  row_count: number;
  column_count: number;
}

export interface PeriodOption {
  id: string;
  label: string;
  start_period?: string;
  end_period?: string;
}

export interface AnalysisRow {
  [key: string]:
    | string
    | number
    | null
    | undefined;
}

export interface AnalysisResult {
  rows: AnalysisRow[];
  columns: string[];
  sum_to_reach?: number;
  summary_sentence?: string;
}

export interface MetricAnalysis {
  unique: AnalysisResult | null;
  mom: Record<string, AnalysisResult>;
  qoq: Record<string, AnalysisResult>;
  yoy: Record<string, AnalysisResult>;
}

export interface MetricPeriods {
  mom: PeriodOption[];
  qoq: PeriodOption[];
  yoy: PeriodOption[];
}

export interface ProjectWiseAnalysis {
  revenue: MetricAnalysis;
  cost: MetricAnalysis;
}

export interface RegionWiseAnalysis {
  [region: string]: {
    revenue: MetricAnalysis;
    cost: MetricAnalysis;
  };
}

export interface DatasetSession {
  dataset: DatasetMetadata;

  mapping: ColumnMapping;

  regions: string[];

  periods: {
    revenue: MetricPeriods;
    cost: MetricPeriods;
  };

  projectWise: ProjectWiseAnalysis;

  regionWise: RegionWiseAnalysis;
}

export type IngestionStatus =
  | "resolved"
  | "needs_clarification"
  | "needs_sheet_selection";

export interface IngestionResponse {
  status: IngestionStatus;

  session?: DatasetSession;

  clarifications?: ClarificationRequest[];

  sheets?: string[];

  filename?: string;

  sheet_name?: string;

  header_row_index?: number | null;

  header_row_confidence?: number | null;
}

export interface WorkbookInspectionResponse {
  status: "success";
  filename: string;
  sheets: string[];
}