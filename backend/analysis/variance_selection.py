"""
Shared logic used by Month-on-Month, Quarter-on-Quarter, and
Year-on-Year analysis: the top/bottom project SELECTION algorithm and
the summary SENTENCE generation. These two steps are identical across
all three analysis types once you have a DataFrame with a 'C' column
representing the relevant variance -- what varies between the three
types is only HOW column C gets computed (M-o-M: month3-month1 of a
3-month chain; Q-o-Q: quarter_b_total - quarter_a_total; Y-o-Y:
year_y_total - year_x_total), which each analysis type's own module
handles before calling finalize_variance_analysis() here.
"""

import pandas as pd


def select_driving_projects(
        df_sorted_desc: pd.DataFrame,
        project_col: str,
        sum_to_reach: float,
        max_projects_allowed: int = 10,
) -> tuple[list[str], list[str]]:
    """
    Selects the projects that "tell the story" of the net change: at
    least 2 from the top + 2 from the bottom of the C-sorted list, then
    grows toward |sumCurrently| >= |sumToReach * 0.9|, capped at
    max_projects_allowed.

    NOTE on the growth condition: the spec says the loop should continue
    "as long as sumCurrently is not equal to sumToReach*0.9". With real,
    discrete revenue/cost values, exact equality will almost never
    occur, so a literal '==' would make the loop run to the 10-project
    cap every time. This implementation stops once sumCurrently has
    REACHED (in magnitude) 90% of sumToReach -- confirmed with the user
    as the intended reading.

    Returns (top_selected, bottom_selected):
        top_selected    -- ordered highest C -> lowest
        bottom_selected -- ordered lowest C -> highest
    """
    n = len(df_sorted_desc)
    projects = df_sorted_desc[project_col].tolist()
    c_values = df_sorted_desc["C"].tolist()

    if n <= 4:
        half = max(1, n // 2)
        top_idx = list(range(0, min(half, n)))
        bottom_idx = list(range(max(half, n - half), n))
        bottom_idx = [i for i in bottom_idx if i not in top_idx]
        top_selected = [projects[i] for i in top_idx]
        bottom_selected = [projects[i] for i in reversed(bottom_idx)]
        return top_selected, bottom_selected

    top_idx = [0, 1]
    bottom_idx = [n - 1, n - 2]

    selected_count = 4
    sum_currently = c_values[0] + c_values[1] + c_values[n - 1] + c_values[n - 2]
    threshold = sum_to_reach * 0.9

    next_top = 2
    next_bottom = n - 3

    if sum_to_reach >= 0:
        while (
                abs(sum_currently) < abs(threshold)
                and selected_count < max_projects_allowed
                and next_top < n
        ):
            top_idx.append(next_top)
            sum_currently += c_values[next_top]
            next_top += 1
            selected_count += 1
    else:
        while (
                abs(sum_currently) < abs(threshold)
                and selected_count < max_projects_allowed
                and next_bottom >= 0
        ):
            bottom_idx.append(next_bottom)
            sum_currently += c_values[next_bottom]
            next_bottom -= 1
            selected_count += 1

    top_selected = [projects[i] for i in top_idx]
    bottom_selected = [projects[i] for i in bottom_idx]

    return top_selected, bottom_selected


def generate_summary_sentence(
        sum_to_reach: float, top_selected: list[str], bottom_selected: list[str]
) -> str:
    """Builds the summary sentence in the format specified in the doc."""
    if sum_to_reach < 0:
        return (
            f"There is a net decrease of {sum_to_reach} amount which is "
            f"primarily arising from the following projects -- "
            f"{', '.join(bottom_selected)} which is partially offset by "
            f"increase in the following projects -- {', '.join(top_selected)}"
        )
    else:
        return (
            f"There is a net increase of {sum_to_reach} amount which is "
            f"primarily arising from the following projects -- "
            f"{', '.join(top_selected)} which is partially offset by "
            f"decrease in the following projects -- {', '.join(bottom_selected)}"
        )


def finalize_variance_analysis(df_with_c: pd.DataFrame, project_col: str) -> dict:
    """
    Given a DataFrame that already has a 'C' column computed (however
    that analysis type computes it), runs the shared final steps:
    sumToReach, sort, select, sentence.

    Returns dict with 'comparison_view', 'sum_to_reach', 'summary_sentence'.
    """
    sum_to_reach = df_with_c["C"].sum()
    sorted_desc = df_with_c.sort_values("C", ascending=False).reset_index(drop=True)

    top_selected, bottom_selected = select_driving_projects(
        sorted_desc, project_col, sum_to_reach
    )
    summary_sentence = generate_summary_sentence(
        sum_to_reach, top_selected, bottom_selected
    )

    return {
        "comparison_view": sorted_desc,
        "sum_to_reach": sum_to_reach,
        "summary_sentence": summary_sentence,
    }