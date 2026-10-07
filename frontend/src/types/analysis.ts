import type {
  AnalysisResult,
  Metric,
  PeriodOption,
  PeriodType,
  Scope,
} from "./dataset";

export interface AnalysisRouteParams {
  scope: Scope;
  metric: Metric;
  period: PeriodType;
  selectionId: string;
  region?: string;
}

export interface PeriodSelectionProps {
  scope: Scope;
  metric: Metric;
  period: Exclude<PeriodType, "unique">;
  region?: string;
}

export interface SelectedAnalysis {
  result: AnalysisResult;
  option?: PeriodOption;
}