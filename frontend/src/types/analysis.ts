export type Scope = "project" | "region";
export type Metric = "revenue" | "cost";
export type Period = "MoM" | "QoQ" | "YoY";

export interface TableData {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

export interface PeriodResult {
  comparison_view: TableData;
  sum_to_reach: number | null;
  summary_sentence: string;
  label?: string;
}

export interface MetricResults {
  available: boolean;
  unique: TableData | null;
  mom: Record<string, PeriodResult>;
  qoq: Record<string, PeriodResult>;
  yoy: Record<string, PeriodResult>;
}

export interface ScopeResults {
  revenue: MetricResults;
  cost: MetricResults;
}

export interface Mapping {
  project_col: string;
  region_col: string | null;
  revenue_month_year_cols: string[];
  cost_month_year_cols: string[];
}

export interface PeriodOption {
  id: string;
  label: string;
  months?: string[];
  quarterAMonths?: string[];
  quarterBMonths?: string[];
  yearAMonths?: string[];
  yearBMonths?: string[];
}

export interface MetricPeriodMetadata {
  mom: PeriodOption[];
  qoq: PeriodOption[];
  yoy: PeriodOption[];
}

export interface PeriodMetadata {
  revenue: MetricPeriodMetadata;
  cost: MetricPeriodMetadata;
}

export interface DatasetSession {
  fileName: string;
  sheetName: string;
  rowCount: number;
  columnCount: number;
  mapping: Mapping;
  regions: string[];
  periods: PeriodMetadata;
  projectWise: ScopeResults;
  regionWise: Record<string, ScopeResults>;
}

export interface ProcessResolvedResponse {
  status: "resolved";
  session: DatasetSession;
}

export interface Candidate {
  column: string;
  score?: number;
  reasons?: string[];
  sample_values?: unknown[];
}

export interface Clarification {
  field: string;
  message: string;
  candidates: Candidate[];
}

export interface ProcessClarificationResponse {
  status: "needs_clarification";
  filename?: string;
  sheetName?: string;
  clarifications: Clarification[];
}

export type ProcessResponse =
  | ProcessResolvedResponse
  | ProcessClarificationResponse;

export interface SheetListResponse {
  filename: string;
  sheets: string[];
}

export interface ProcessingStage {
  key: "upload" | "ingestion" | "project" | "region" | "finalizing";
  label: string;
}

export const PROCESSING_STAGES: ProcessingStage[] = [
  {
    key: "upload",
    label: "Importing dataset",
  },
  {
    key: "ingestion",
    label: "Detecting columns",
  },
  {
    key: "project",
    label: "Computing project-wise analysis",
  },
  {
    key: "region",
    label: "Computing region-wise analysis",
  },
  {
    key: "finalizing",
    label: "Finalizing results",
  },
];