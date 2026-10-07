"""
Excel export functionality.

This module formats an already-computed DataFrame.
It does not perform analysis.
"""

from io import BytesIO

import pandas as pd


def _write_dataframe(
        df: pd.DataFrame,
        writer,
        sheet_name: str,
) -> None:
    df.to_excel(
        writer,
        sheet_name=sheet_name,
        index=False,
    )

    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#D9E1F2",
            "border": 1,
        }
    )

    for col_num, column_name in enumerate(
            df.columns
    ):
        worksheet.write(
            0,
            col_num,
            column_name,
            header_format,
        )

        if df.empty:
            max_content_width = 0
        else:
            max_content_width = (
                df[column_name]
                .astype(str)
                .map(len)
                .max()
            )

        column_width = (
                max(
                    len(str(column_name)),
                    int(max_content_width),
                )
                + 2
        )

        worksheet.set_column(
            col_num,
            col_num,
            min(column_width, 60),
        )

    worksheet.freeze_panes(1, 0)


def export_dataframe_to_excel(
        df: pd.DataFrame,
        output_path: str,
        sheet_name: str = "Analysis",
) -> None:
    with pd.ExcelWriter(
            output_path,
            engine="xlsxwriter",
    ) as writer:
        _write_dataframe(
            df,
            writer,
            sheet_name,
        )


def export_dataframe_to_excel_bytes(
        df: pd.DataFrame,
        sheet_name: str = "Analysis",
) -> bytes:
    output = BytesIO()

    with pd.ExcelWriter(
            output,
            engine="xlsxwriter",
    ) as writer:
        _write_dataframe(
            df,
            writer,
            sheet_name,
        )

    return output.getvalue()