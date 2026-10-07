"""
Excel export functionality.

This module only handles converting an already-computed DataFrame
into an Excel workbook.

It does not perform financial analysis.
"""

import pandas as pd


def export_dataframe_to_excel(
        df: pd.DataFrame,
        output_path: str,
        sheet_name: str = "Analysis",
) -> None:
    """
    Export an already-computed DataFrame to a formatted Excel file.
    """

    with pd.ExcelWriter(
            output_path,
            engine="xlsxwriter",
    ) as writer:

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

        for col_num, column_name in enumerate(df.columns):

            worksheet.write(
                0,
                col_num,
                column_name,
                header_format,
            )

            max_content_width = (
                df[column_name]
                .astype(str)
                .map(len)
                .max()
            )

            column_width = (
                    max(
                        len(str(column_name)),
                        max_content_width,
                    )
                    + 2
            )

            worksheet.set_column(
                col_num,
                col_num,
                column_width,
            )

        worksheet.freeze_panes(1, 0)