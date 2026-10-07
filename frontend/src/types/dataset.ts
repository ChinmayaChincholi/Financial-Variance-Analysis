export type Scope = "project" | "region";

export type Metric = "revenue" | "cost";

export type PeriodType = "unique" | "MoM" | "QoQ" | "YoY";

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
  sample_values: string[];
}

export interface ClarificationRequest {
  field: string;
  message: string;
  candidates: ClarificationCandidate[];
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

export interface UniqueRow {
  project?: string;
  region?: string;
  values: Record<string, number | string | null>;
}

export interface AnalysisRow {
  [key: string]: string | number | null | undefined;
}

export interface AnalysisResult {
  rows: AnalysisRow[];
  columns: string[];
  comparison_view?: AnalysisRow[];
  sum_to_reach?: number;
  summary_sentence?: string;
}

export interface MetricAnalysis {
  unique: AnalysisResult;
  mom: Record<string, AnalysisResult>;
  qoq: Record<string, AnalysisResult>;
  yoy: Record<string, AnalysisResult>;
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
    revenue: {
      mom: PeriodOption[];
      qoq: PeriodOption[];
      yoy: PeriodOption[];
    };
    cost: {
      mom: PeriodOption[];
      qoq: PeriodOption[];
      yoy: PeriodOption[];
    };
  };
  projectWise: ProjectWiseAnalysis;
  regionWise: RegionWiseAnalysis;
}

export interface IngestionResponse {
  status: "resolved" | "needs_clarification";
  session?: DatasetSession;
  clarifications?: ClarificationRequest[];
  header_row_index?: number | null;
  header_row_confidence?: number | null;
}