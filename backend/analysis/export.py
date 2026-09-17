"""
Exports an analysis view (currently: Unique Projects & Revenue/Cost)
to a formatted Excel file, per the doc's requirement that the client
be able to export this view as a spreadsheet.

Lives in analysis/ because it operates on an already-computed
DataFrame -- it doesn't interpret column names or dates, it just
formats and writes whatever view it's given.
"""

import pandas as pd


def export_view_to_excel(
        df: pd.DataFrame,
        output_path: str,
        sheet_name: str = "Analysis",
) -> None:
    """
    Writes a DataFrame to a formatted .xlsx file: bold header row,
    frozen header (so it stays visible on scroll), and auto-sized
    columns based on content width.

    Parameters
    ----------
    df : the view to export (e.g. the output of get_unique_projects).
    output_path : path to write the .xlsx file to.
    sheet_name : name of the worksheet.
    """
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D9E1F2", "border": 1}
        )
        for col_num, column_name in enumerate(df.columns):
            worksheet.write(0, col_num, column_name, header_format)

            # Auto-size: widest of the header text or the longest
            # value in that column, with a little padding.
            max_content_width = df[column_name].astype(str).map(len).max()
            column_width = max(len(str(column_name)), max_content_width) + 2
            worksheet.set_column(col_num, col_num, column_width)

        worksheet.freeze_panes(1, 0)  # freeze the header row