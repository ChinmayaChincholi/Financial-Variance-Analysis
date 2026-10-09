"""
Shared Excel sheet reader.

Uses the much faster `calamine` engine when `python-calamine` is
installed, and falls back to pandas' default engine (openpyxl)
otherwise, so the app keeps working either way.
"""

import pandas as pd

try:
    import python_calamine  # noqa: F401

    _ENGINE: str | None = "calamine"
except ImportError:
    _ENGINE = None

def read_sheet(
        path: str,
        sheet_name: str,
        header: int | None,
        nrows: int | None = None,
) -> pd.DataFrame:
    kwargs: dict = {}

    if _ENGINE is not None:
        kwargs["engine"] = _ENGINE

    if nrows is not None:
        kwargs["nrows"] = nrows

    return pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header,
        **kwargs,
    )