"""
Resolves which Month-Year columns represent Revenue and which represent
Cost, when the month columns themselves carry no revenue/cost wording at
all (validated against Financial_Dataset.xlsx: columns named 'Apr-25'
.. 'Mar-26' have zero lexical signal of their own).

Strategy: group the date-parseable columns into CONTIGUOUS blocks (by
column position), then classify each block using whatever context is
available, in order of decreasing reliability:

  1. Explicit revenue/cost wording on the month header itself
     ("Revenue Apr 2026") -- most reliable, when present.
  2. The header text of the column(s) immediately flanking the block
     (e.g. 'Revenue Book currency' right before a block, 'YTD Revenue$'
     right after) -- this is what actually resolves the real dataset.
  3. If a block still can't be classified: if there are exactly two
     unresolved blocks, ask the user to label the pair in one question
     ("which of these is Revenue, which is Cost?"); if there's exactly
     one block, ask once whether it's Revenue or Cost; more than two
     unresolved blocks always goes to the user -- this module never
     guesses at that point.
"""

from dataclasses import dataclass, field

from ingestion.column_profiling import ColumnProfile
from ingestion.column_scoring import _header_match_score
from ingestion.reference_data import (
    COST_HEADER_SYNONYMS,
    REVENUE_HEADER_SYNONYMS,
)

NEIGHBOR_LOOKUP_DISTANCE = 2


@dataclass
class MonthYearBlock:
    columns: list[str]
    start_position: int
    end_position: int
    metric_type: str | None = None
    reasons: list[str] = field(default_factory=list)


def group_into_contiguous_blocks(
        profiles: list[ColumnProfile],
) -> list[MonthYearBlock]:
    """
    Groups date-parseable columns that sit next to each other (by
    position) into blocks. Two month columns separated by a non-date
    column are treated as separate blocks.

    Only intended to be called on columns that did NOT already resolve
    via their own explicit label (see resolve_metric_blocks) -- a
    labeled column breaks contiguity for its unlabeled neighbors just
    like a non-date column would, which is the correct behavior: it's
    already a boundary between two different things.
    """
    month_profiles = sorted(
        (
            p
            for p in profiles
            if p.is_month_year
        ),
        key=lambda p: p.position,
    )

    if not month_profiles:
        return []

    blocks: list[MonthYearBlock] = []
    current = [month_profiles[0]]

    for prev, curr in zip(
            month_profiles,
            month_profiles[1:],
    ):
        if curr.position == prev.position + 1:
            current.append(curr)
        else:
            blocks.append(
                _finalize_block(current)
            )
            current = [curr]

    blocks.append(
        _finalize_block(current)
    )

    return blocks


def _finalize_block(
        profiles_in_block: list[ColumnProfile],
) -> MonthYearBlock:
    return MonthYearBlock(
        columns=[
            p.name
            for p in profiles_in_block
        ],
        start_position=profiles_in_block[0].position,
        end_position=profiles_in_block[-1].position,
    )


def _neighbor_headers(
        all_profiles_by_position: dict,
        block: MonthYearBlock,
) -> list[str]:
    neighbors = []

    for offset in range(
            1,
            NEIGHBOR_LOOKUP_DISTANCE + 1,
    ):
        before_pos = block.start_position - offset
        after_pos = block.end_position + offset

        if before_pos in all_profiles_by_position:
            neighbors.append(
                all_profiles_by_position[before_pos].name
            )

        if after_pos in all_profiles_by_position:
            neighbors.append(
                all_profiles_by_position[after_pos].name
            )

    return neighbors


def _classify_via_headers(
        header_texts: list[str],
) -> tuple[str | None, list[str]]:
    reasons = []

    best_revenue = 0.0
    best_cost = 0.0

    for h in header_texts:
        rev_score, rev_syn = _header_match_score(
            h,
            REVENUE_HEADER_SYNONYMS,
        )

        cost_score, cost_syn = _header_match_score(
            h,
            COST_HEADER_SYNONYMS,
        )

        if rev_score > best_revenue:
            best_revenue = rev_score

        if cost_score > best_cost:
            best_cost = cost_score

        if rev_score:
            reasons.append(
                f"neighbor '{h}' resembles revenue wording "
                f"({rev_score:.2f})"
            )

        if cost_score:
            reasons.append(
                f"neighbor '{h}' resembles cost wording "
                f"({cost_score:.2f})"
            )

    if best_revenue == 0.0 and best_cost == 0.0:
        return None, reasons

    if best_revenue >= best_cost + 0.15:
        return "revenue", reasons

    if best_cost >= best_revenue + 0.15:
        return "cost", reasons

    return None, reasons


def classify_block(
        block: MonthYearBlock,
        all_profiles: list[ColumnProfile],
) -> MonthYearBlock:
    """
    Classifies one block in place (returns the same object, mutated,
    for convenience) using:

      1. explicit wording on the block's own headers
      2. neighboring column headers
      3. clarification if neither provides enough evidence
    """
    by_position = {
        p.position: p
        for p in all_profiles
    }

    # Signal 1: explicit wording on the block's own column headers.
    own_type, own_reasons = _classify_via_headers(
        block.columns
    )

    if own_type:
        block.metric_type = own_type
        block.reasons = own_reasons
        return block

    # Signal 2: neighboring column headers.
    neighbor_headers = _neighbor_headers(
        by_position,
        block,
    )

    neighbor_type, neighbor_reasons = _classify_via_headers(
        neighbor_headers
    )

    if neighbor_type:
        block.metric_type = neighbor_type
        block.reasons = neighbor_reasons
        return block

    block.metric_type = None
    block.reasons = [
        "no header or neighbor signal was strong enough "
        "to classify this block"
    ]

    return block


@dataclass
class MetricBlockResolution:
    revenue_cols: list[str]
    cost_cols: list[str]
    unresolved_blocks: list[MonthYearBlock]
    needs_clarification: bool
    message: str | None = None


def resolve_metric_blocks(
        profiles: list[ColumnProfile],
) -> MetricBlockResolution:
    """
    Top-level entry point.

    Two-pass approach:
      Pass 1 -- check EVERY month-year column's own header individually
      for explicit revenue/cost wording, before any grouping happens.
      This matters because two adjacently-positioned columns can each
      carry their own explicit label ("Revenue Jan 2026" right next to
      "Cost Jan 2026") -- grouping by position first would have merged
      them into one mixed block and made the per-column labels
      unreadable (found via testing, not obvious up front).

      Pass 2 -- group whatever's left (columns with no explicit label of
      their own) into contiguous blocks by position, and classify each
      block via neighbor-header context, then the multi-block fallback
      rules described in the module docstring.
    """
    month_profiles = [
        p
        for p in profiles
        if p.is_month_year
    ]

    if not month_profiles:
        return MetricBlockResolution(
            revenue_cols=[],
            cost_cols=[],
            unresolved_blocks=[],
            needs_clarification=True,
            message=(
                "No Month-Year columns were found "
                "in the dataset at all."
            ),
        )

    revenue_cols: list[str] = []
    cost_cols: list[str] = []
    unlabeled_profiles: list[ColumnProfile] = []

    for p in month_profiles:
        own_type, _ = _classify_via_headers(
            [p.name]
        )

        if own_type == "revenue":
            revenue_cols.append(p.name)

        elif own_type == "cost":
            cost_cols.append(p.name)

        else:
            unlabeled_profiles.append(p)

    blocks = group_into_contiguous_blocks(
        unlabeled_profiles
    )

    classified = [
        classify_block(
            b,
            profiles,
        )
        for b in blocks
    ]

    unresolved = [
        b
        for b in classified
        if b.metric_type is None
    ]

    for b in classified:
        if b.metric_type == "revenue":
            revenue_cols.extend(b.columns)

        elif b.metric_type == "cost":
            cost_cols.extend(b.columns)

    if not unresolved:
        return MetricBlockResolution(
            revenue_cols=revenue_cols,
            cost_cols=cost_cols,
            unresolved_blocks=[],
            needs_clarification=False,
        )

    if (
            len(unresolved) == 1
            and not revenue_cols
            and not cost_cols
    ):
        # Exactly one block total, and it's unresolved:
        # ask once which metric it is.
        return MetricBlockResolution(
            revenue_cols=[],
            cost_cols=[],
            unresolved_blocks=unresolved,
            needs_clarification=True,
            message=(
                "Do these Month-Year columns represent "
                "Revenue or Cost?"
            ),
        )

    if (
            len(unresolved) == 1
            and (bool(revenue_cols) != bool(cost_cols))
    ):
        # One metric resolved, exactly one block left unresolved:
        # very likely the other metric, but still confirm rather than
        # assume.
        missing_metric = (
            "Cost"
            if revenue_cols
            else "Revenue"
        )

        return MetricBlockResolution(
            revenue_cols=revenue_cols,
            cost_cols=cost_cols,
            unresolved_blocks=unresolved,
            needs_clarification=True,
            message=(
                f"These Month-Year columns are most likely "
                f"{missing_metric}, based on there being no other "
                f"metric block left -- please confirm."
            ),
        )

    return MetricBlockResolution(
        revenue_cols=revenue_cols,
        cost_cols=cost_cols,
        unresolved_blocks=unresolved,
        needs_clarification=True,
        message=(
            "Please label each of the highlighted Month-Year "
            "column groups as Revenue or Cost."
        ),
    )