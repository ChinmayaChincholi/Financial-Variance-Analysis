"""
Hand-computed test cases for analyze_month_on_month.

The spec doc doesn't give a full worked M-o-M example (only the simpler
'unique projects' example), so these fixtures are constructed and their
expected outputs are computed by hand, shown step-by-step below.

--------------------------------------------------------------------
CASE 1: positive sumToReach (net increase), growth from the TOP
--------------------------------------------------------------------
6 projects, month1 = month2 = 100 for all (so A = 0 everywhere, isolating
C to just (month3 - month1)):

    Project | month1 | month2 | month3 | C
    P1      | 100    | 100    | 200    | 100
    P2      | 100    | 100    | 180    | 80
    P3      | 100    | 100    | 160    | 60
    P4      | 100    | 100    | 140    | 40
    P5      | 100    | 100    | 90     | -10
    P6      | 100    | 100    | 50     | -50

sumToReach = 100+80+60+40-10-50 = 220 (positive -> grow from top)

Sorted by C descending: P1(100), P2(80), P3(60), P4(40), P5(-10), P6(-50)

top2 = P1, P2 | bottom2 = P5, P6 (the last two rows, i.e. lowest values)
sumCurrently = 100+80-10-50 = 120
threshold = 220 * 0.9 = 198

Grow from top (sumToReach positive):
  add P3 (60): sumCurrently = 180 -> |180| < |198| -> keep growing
  add P4 (40): sumCurrently = 220 -> |220| >= |198| -> stop

Final selection: top_selected = [P1, P2, P3, P4] (highest->lowest)
                 bottom_selected = [P6, P5] (lowest->highest: -50 then -10)

--------------------------------------------------------------------
CASE 2: negative sumToReach (net decrease), growth from the BOTTOM
--------------------------------------------------------------------
    Project | month1 | month2 | month3 | C
    Q1      | 100    | 100    | 0      | -100
    Q2      | 100    | 100    | 20     | -80
    Q3      | 100    | 100    | 40     | -60
    Q4      | 100    | 100    | 60     | -40
    Q5      | 100    | 100    | 110    | 10
    Q6      | 100    | 100    | 150    | 50

sumToReach = -100-80-60-40+10+50 = -220 (negative -> grow from bottom)

Sorted by C descending: Q6(50), Q5(10), Q4(-40), Q3(-60), Q2(-80), Q1(-100)

top2 = Q6, Q5 | bottom2 = Q2, Q1 (the last two rows, i.e. lowest values)
sumCurrently = 50+10-80-100 = -120
threshold = -220 * 0.9 = -198

Grow from bottom (sumToReach negative):
  add Q3 (-60): sumCurrently = -180 -> |-180| < |-198| -> keep growing
  add Q4 (-40): sumCurrently = -220 -> |-220| >= |-198| -> stop

Final selection: top_selected = [Q6, Q5] (highest->lowest)
                 bottom_selected = [Q1, Q2, Q3, Q4] (lowest->highest:
                 -100, -80, -60, -40)
"""

import pandas as pd
from analysis.month_on_month import analyze_month_on_month


def _build_case_1():
    return pd.DataFrame(
        {
            "Project Name": ["P1", "P2", "P3", "P4", "P5", "P6"],
            "Apr 2026": [100, 100, 100, 100, 100, 100],
            "May 2026": [100, 100, 100, 100, 100, 100],
            "Jun 2026": [200, 180, 160, 140, 90, 50],
        }
    )


def _build_case_2():
    return pd.DataFrame(
        {
            "Project Name": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
            "Apr 2026": [100, 100, 100, 100, 100, 100],
            "May 2026": [100, 100, 100, 100, 100, 100],
            "Jun 2026": [0, 20, 40, 60, 110, 150],
        }
    )


def test_positive_sum_to_reach_grows_from_top():
    df = _build_case_1()
    result = analyze_month_on_month(
        df, project_col="Project Name", month_cols=["Apr 2026", "May 2026", "Jun 2026"]
    )

    assert result["sum_to_reach"] == 220

    view = result["comparison_view"]
    # Confirm variance columns computed correctly for the top row (P1).
    p1 = view[view["Project Name"] == "P1"].iloc[0]
    assert p1["A"] == 0
    assert p1["B"] == 100
    assert p1["C"] == 100

    sentence = result["summary_sentence"]
    assert "net increase of 220" in sentence
    assert "P1, P2, P3, P4" in sentence
    assert "P6, P5" in sentence


def test_negative_sum_to_reach_grows_from_bottom():
    df = _build_case_2()
    result = analyze_month_on_month(
        df, project_col="Project Name", month_cols=["Apr 2026", "May 2026", "Jun 2026"]
    )

    assert result["sum_to_reach"] == -220

    sentence = result["summary_sentence"]
    assert "net decrease of -220" in sentence
    assert "Q1, Q2, Q3, Q4" in sentence
    assert "Q6, Q5" in sentence


def test_raises_on_wrong_number_of_month_cols():
    df = _build_case_1()
    try:
        analyze_month_on_month(
            df, project_col="Project Name", month_cols=["Apr 2026", "May 2026"]
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_handles_projects_with_duplicate_rows():
    """Confirms dedup-and-sum (via get_unique_projects) happens BEFORE
    variance calculation, not after -- a project appearing twice in the
    raw data must be summed first, then have its variance computed once,
    not have two separate variance rows."""
    df = pd.DataFrame(
        {
            "Project Name": ["A", "B", "A"],
            "Apr 2026": [100, 100, 300],
            "May 2026": [200, 120, 200],
            "Jun 2026": [150, 160, 180],
        }
    )
    result = analyze_month_on_month(
        df, project_col="Project Name", month_cols=["Apr 2026", "May 2026", "Jun 2026"]
    )
    view = result["comparison_view"]
    assert len(view) == 2  # exactly one row per distinct project

    a_row = view[view["Project Name"] == "A"].iloc[0]
    # A's summed values (from the doc's own example): 400, 400, 330
    assert a_row["Apr 2026"] == 400
    assert a_row["May 2026"] == 400
    assert a_row["Jun 2026"] == 330
    assert a_row["C"] == 330 - 400  # -70