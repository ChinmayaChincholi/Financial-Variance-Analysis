"""
Tests for analysis/period_aggregation.py -- now containing ONLY the
pure summation function. Its date-parsing/grouping counterpart moved
to ingestion/period_grouping.py and is tested separately in
test_ingestion_period_grouping.py.
"""

import pandas as pd
from analysis.period_aggregation import aggregate_periods


def test_aggregate_periods_sums_correctly():
    df = pd.DataFrame(
        {
            "Jan 2026": [10, 20],
            "Feb 2026": [5, 5],
            "Mar 2026": [0, 100],
        }
    )
    result = aggregate_periods(df, {"Q1 2026": ["Jan 2026", "Feb 2026", "Mar 2026"]})
    assert result["Q1 2026"].tolist() == [15, 125]


def test_aggregate_periods_raises_on_missing_column():
    df = pd.DataFrame({"Jan 2026": [10]})
    try:
        aggregate_periods(df, {"Q1 2026": ["Jan 2026", "Feb 2026"]})
        assert False, "expected ValueError"
    except ValueError:
        pass