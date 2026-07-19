import logging
log = logging.getLogger(__name__)
import os
import re
import pandas as pd
from typing import List


_INVALID_SHEET_CHARS = re.compile(r'[\\/*?:\[\]]')


def _make_sheet_name(raw_name: str, used_names: set[str]) -> str:
    """Return a legal, unique Excel sheet name."""
    base_name = str(raw_name or "").strip()
    base_name = _INVALID_SHEET_CHARS.sub("_", base_name)
    base_name = re.sub(r"\s+", " ", base_name).strip()
    base_name = (base_name or "Sheet")[:31] or "Sheet"

    candidate = base_name
    counter = 1
    while candidate in used_names:
        counter += 1
        suffix = f"_{counter}"
        trimmed = base_name[: max(1, 31 - len(suffix))].rstrip()
        candidate = f"{trimmed}{suffix}"
    used_names.add(candidate)
    return candidate


def _remove_default_sheet_if_safe(workbook) -> None:
    default_sheet = workbook["Sheet"] if "Sheet" in workbook.sheetnames else None
    if default_sheet is None:
        return
    other_sheets = [sheet for sheet in workbook.worksheets if sheet is not default_sheet]
    visible_others = [sheet for sheet in other_sheets if sheet.sheet_state == "visible"]
    if visible_others:
        workbook.remove(default_sheet)


def _ensure_visible_workbook(workbook) -> None:
    if not workbook.worksheets:
        workbook.create_sheet(title="Sheet1")

    visible_indexes = [
        idx for idx, sheet in enumerate(workbook.worksheets)
        if sheet.sheet_state == "visible"
    ]
    if not visible_indexes:
        workbook.worksheets[0].sheet_state = "visible"
        visible_indexes = [0]

    workbook.active = visible_indexes[0]


def export_to_excel(datasource, tables: List[str], filepath: str) -> dict:
    """
    Query *tables* from *datasource* and write each as a separate sheet
    in an Excel file at *filepath*.

    Returns a metadata dict on success.
    Raises ValueError if no table could be exported.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    export_items = []
    used_sheet_names: set[str] = set()

    for table in tables:
        try:
            df, err = datasource.execute_query(f'SELECT * FROM "{table}"')
            if err or df is None or df.empty:
                continue
            export_items.append({
                "table": table,
                "sheet_name": _make_sheet_name(table, used_sheet_names),
                "dataframe": df,
            })
        except Exception as exc:
            log.warning("[excel_export] 导出表 %r 失败: %s", table, exc)
            continue

    if not export_items:
        raise ValueError("暂无可导出的数据")

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for item in export_items:
            item["dataframe"].to_excel(writer, sheet_name=item["sheet_name"], index=False)
            writer.book[item["sheet_name"]].sheet_state = "visible"

        _remove_default_sheet_if_safe(writer.book)
        _ensure_visible_workbook(writer.book)

    return {
        "filepath": filepath,
        "written_count": len(export_items),
        "exported_tables": [item["table"] for item in export_items],
        "sheet_names": [item["sheet_name"] for item in export_items],
    }
