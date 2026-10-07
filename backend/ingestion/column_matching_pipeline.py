"""
Top-level ingestion pipeline.

Responsibilities:
- detect the header row
- profile columns
- resolve Project Name
- resolve optional Region
- resolve Revenue/Cost Month-Year blocks
- return a complete ColumnMapping
- support a second pass after user clarification

This module does not perform financial analysis.
"""

import re

import pandas as pd

from ingestion.column_profiling import (
    drop_placeholder_or_empty_columns,
    profile_columns,
)
from ingestion.column_scoring import (
    ScoringWeights,
    resolve_field,
    score_project_candidates,
    score_region_candidates,
)
from ingestion.header_detection import detect_header_row
from ingestion.metric_block_resolver import resolve_metric_blocks
from ingestion.schema import (
    ClarificationRequest,
    ColumnCandidateOut,
    ColumnMapping,
    IngestionResult,
)

HEADER_ROW_CONFIDENCE_FLOOR = 0.55

NO_REGION_CHOICE = "__none__"

METRIC_BLOCK_FIELD_PREFIX = "metric_block_"


def _to_candidate_out(candidates) -> list[ColumnCandidateOut]:
    return [
        ColumnCandidateOut(
            column=c.column,
            score=c.score,
            reasons=c.reasons,
            sample_values=c.sample_values,
        )
        for c in candidates
    ]


def _block_label(columns: list[str]) -> str:
    if len(columns) == 1:
        return columns[0]

    return (
        f"{columns[0]} .. {columns[-1]} "
        f"({len(columns)} columns)"
    )


def _validate_column_choice(
        df: pd.DataFrame,
        field: str,
        chosen_column: str,
) -> str:
    if chosen_column not in df.columns:
        raise ValueError(
            f"The selected column '{chosen_column}' for "
            f"{field} does not exist in the dataset."
        )

    return chosen_column


def _parse_header_choice(value: str) -> int:
    """
    Frontend sends human-readable values such as:

        Row 1
        Row 2

    Internally header indexes remain zero-based.
    """

    match = re.fullmatch(
        r"\s*Row\s+(\d+)\s*",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        row_number = int(match.group(1))

        if row_number < 1:
            raise ValueError(
                "Header row selection must start at Row 1."
            )

        return row_number - 1

    if value.strip().isdigit():
        row_number = int(value.strip())

        if row_number < 0:
            raise ValueError(
                "Invalid header row selection."
            )

        return row_number

    raise ValueError(
        f"Invalid header row selection '{value}'."
    )


def _build_metric_clarifications(
        unresolved_blocks,
) -> list[ClarificationRequest]:
    clarifications: list[ClarificationRequest] = []

    for index, block in enumerate(unresolved_blocks):
        label = _block_label(block.columns)

        clarifications.append(
            ClarificationRequest(
                field=f"{METRIC_BLOCK_FIELD_PREFIX}{index}",
                message=(
                    f"Which metric does this Month-Year "
                    f"column block represent?\n\n{label}"
                ),
                candidates=[
                    ColumnCandidateOut(
                        column="Revenue",
                        score=0.0,
                        reasons=[],
                        sample_values=[],
                    ),
                    ColumnCandidateOut(
                        column="Cost",
                        score=0.0,
                        reasons=[],
                        sample_values=[],
                    ),
                ],
                allow_none=False,
            )
        )

    return clarifications


def _resolve_dataframe(
        df: pd.DataFrame,
        choices: dict[str, str] | None = None,
        header_row_index: int | None = None,
        header_row_confidence: float | None = None,
        weights: ScoringWeights = ScoringWeights(),
) -> IngestionResult:
    """
    Resolve one already-headered DataFrame.

    `choices` contains user decisions from the frontend.
    """

    choices = choices or {}

    df = drop_placeholder_or_empty_columns(df)

    profiles = profile_columns(df)

    clarifications: list[ClarificationRequest] = []

    # ---------------------------------------------------------
    # PROJECT NAME
    # ---------------------------------------------------------

    project_scores = score_project_candidates(
        profiles,
        df,
        weights=weights,
    )

    project_resolution = resolve_field(
        project_scores,
        "Project Name",
        weights=weights,
    )

    if "project_name" in choices:
        project_col = _validate_column_choice(
            df,
            "Project Name",
            choices["project_name"],
        )
    elif project_resolution.resolved_column is not None:
        project_col = project_resolution.resolved_column
    else:
        clarifications.append(
            ClarificationRequest(
                field="project_name",
                message=(
                        project_resolution.message
                        or "Please select the Project Name column."
                ),
                candidates=_to_candidate_out(
                    project_resolution.candidates
                ),
            )
        )
        project_col = None

    # ---------------------------------------------------------
    # REGION
    # ---------------------------------------------------------

    region_scores = score_region_candidates(
        profiles,
        weights=weights,
    )

    region_resolution = resolve_field(
        region_scores,
        "Region",
        weights=weights,
    )

    region_col: str | None

    if choices.get("region") == NO_REGION_CHOICE:
        region_col = None

    elif "region" in choices:
        region_col = _validate_column_choice(
            df,
            "Region",
            choices["region"],
        )

    elif region_resolution.resolved_column is not None:
        region_col = region_resolution.resolved_column

    elif region_scores and region_resolution.needs_clarification:
        clarifications.append(
            ClarificationRequest(
                field="region",
                message=(
                        region_resolution.message
                        or "Please select the Region column."
                ),
                candidates=_to_candidate_out(
                    region_resolution.candidates
                ),
                allow_none=True,
            )
        )
        region_col = None

    else:
        # No region-like column exists.
        # Region is optional, so this is valid.
        region_col = None

    # ---------------------------------------------------------
    # REVENUE / COST MONTH-YEAR BLOCKS
    # ---------------------------------------------------------

    metric_resolution = resolve_metric_blocks(
        profiles
    )

    revenue_cols = list(
        metric_resolution.revenue_cols
    )

    cost_cols = list(
        metric_resolution.cost_cols
    )

    for index, block in enumerate(
            metric_resolution.unresolved_blocks
    ):
        field = (
            f"{METRIC_BLOCK_FIELD_PREFIX}{index}"
        )

        choice = choices.get(field)

        if choice is None:
            clarifications.extend(
                _build_metric_clarifications(
                    [block]
                )
            )
            continue

        normalized_choice = choice.strip().lower()

        if normalized_choice not in {
            "revenue",
            "cost",
        }:
            raise ValueError(
                f"Invalid metric choice '{choice}' "
                f"for {field}. Expected Revenue or Cost."
            )

        if normalized_choice == "revenue":
            revenue_cols.extend(block.columns)
        else:
            cost_cols.extend(block.columns)

    # ---------------------------------------------------------
    # FINAL VALIDATION
    # ---------------------------------------------------------

    if clarifications:
        return IngestionResult(
            status="needs_clarification",
            clarifications=clarifications,
            header_row_index=header_row_index,
            header_row_confidence=header_row_confidence,
        )

    if project_col is None:
        raise ValueError(
            "A Project Name column is required."
        )

    if not revenue_cols and not cost_cols:
        raise ValueError(
            "No Revenue or Cost Month-Year columns "
            "could be resolved from the dataset."
        )

    overlap = set(revenue_cols) & set(cost_cols)

    if overlap:
        raise ValueError(
            "The following Month-Year columns were assigned "
            f"to both Revenue and Cost: {sorted(overlap)}"
        )

    # Preserve the actual dataset column names.
    mapping = ColumnMapping(
        project_col=project_col,
        region_col=region_col,
        revenue_month_year_cols=revenue_cols,
        cost_month_year_cols=cost_cols,
    )

    return IngestionResult(
        status="resolved",
        column_mapping=mapping,
        header_row_index=header_row_index,
        header_row_confidence=header_row_confidence,
    )


def run_ingestion(
        path: str,
        sheet_name: str,
        weights: ScoringWeights = ScoringWeights(),
) -> IngestionResult:
    """
    Run automatic ingestion against one workbook sheet.
    """

    raw = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=None,
    )

    header_result = detect_header_row(raw)

    if (
            header_result.confidence
            < HEADER_ROW_CONFIDENCE_FLOOR
    ):
        return IngestionResult(
            status="needs_clarification",
            clarifications=[
                ClarificationRequest(
                    field="header_row",
                    message=(
                        "Couldn't confidently identify which "
                        "row contains the column headers. "
                        "Please select the correct row."
                    ),
                    candidates=[
                        ColumnCandidateOut(
                            column=(
                                f"Row {r['row_index'] + 1}"
                            ),
                            score=r["score"],
                            reasons=[],
                            sample_values=r["preview"],
                        )
                        for r in header_result.candidate_rows[
                            :5
                        ]
                    ],
                )
            ],
            header_row_index=(
                header_result.header_row_index
            ),
            header_row_confidence=(
                header_result.confidence
            ),
        )

    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header_result.header_row_index,
    )

    return _resolve_dataframe(
        df,
        header_row_index=(
            header_result.header_row_index
        ),
        header_row_confidence=(
            header_result.confidence
        ),
        weights=weights,
    )


def run_ingestion_on_dataframe(
        df: pd.DataFrame,
        weights: ScoringWeights = ScoringWeights(),
        header_row_index: int | None = None,
        header_row_confidence: float | None = None,
) -> IngestionResult:
    """
    Run ingestion against an already-headered DataFrame.

    Primarily useful for tests and clarification workflows.
    """

    return _resolve_dataframe(
        df,
        header_row_index=header_row_index,
        header_row_confidence=header_row_confidence,
        weights=weights,
    )


def resolve_ingestion_with_choices(
        path: str,
        sheet_name: str,
        choices: dict[str, str],
        weights: ScoringWeights = ScoringWeights(),
) -> IngestionResult:
    """
    Re-run ingestion using explicit decisions made by the user.

    This is the authoritative second pass used by the frontend
    clarification page.
    """

    raw = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=None,
    )

    if "header_row" in choices:
        header_row_index = _parse_header_choice(
            choices["header_row"]
        )

        if (
                header_row_index < 0
                or header_row_index >= len(raw)
        ):
            raise ValueError(
                f"Selected header row "
                f"{header_row_index + 1} is outside "
                f"the worksheet."
            )

        header_row_confidence = None

    else:
        header_result = detect_header_row(raw)

        if (
                header_result.confidence
                < HEADER_ROW_CONFIDENCE_FLOOR
        ):
            return run_ingestion(
                path,
                sheet_name,
                weights=weights,
            )

        header_row_index = (
            header_result.header_row_index
        )
        header_row_confidence = (
            header_result.confidence
        )

    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header_row_index,
    )

    return _resolve_dataframe(
        df,
        choices=choices,
        header_row_index=header_row_index,
        header_row_confidence=header_row_confidence,
        weights=weights,
    )


def apply_user_choice(
        result: IngestionResult,
        field: str,
        chosen_column: str,
) -> None:
    """
    Backward-compatible helper retained for existing tests/callers.
    """

    result.clarifications = [
        clarification
        for clarification in result.clarifications
        if clarification.field != field
    ]

    if not result.clarifications:
        result.status = "resolved"