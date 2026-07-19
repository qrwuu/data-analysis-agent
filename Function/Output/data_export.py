"""Export already-selected data frames to XLSX, CSV, or PDF."""
from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path

import pandas as pd

from .excel_export import _ensure_visible_workbook, _make_sheet_name, _remove_default_sheet_if_safe


def _safe_stem(value: str) -> str:
    return re.sub(r"[^\w.-]+", "_", str(value or "data")).strip("._") or "data"


def _write_pdf(items: list[dict], filepath: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

    # ReportLab's built-in CID font renders simplified Chinese without relying
    # on a machine-specific font file.
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    style = styles["BodyText"]
    style.fontName = "STSong-Light"
    style.fontSize = 8
    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
    story = []
    for index, item in enumerate(items):
        frame = item["dataframe"].fillna("").astype(str)
        # A PDF is readable rather than a database dump. CSV/XLSX remain the
        # lossless formats for very large exports.
        truncated = len(frame) > 5000
        if truncated:
            frame = frame.head(5000)
        story.append(Paragraph(str(item["name"]), styles["Heading2"]))
        if truncated:
            story.append(Paragraph("PDF 仅展示前 5000 行；请导出 CSV 或 Excel 获取完整数据。", style))
        data = [[Paragraph(str(column), style) for column in frame.columns]]
        data.extend([[Paragraph(value[:300], style) for value in row] for row in frame.values.tolist()])
        widths = [((landscape(A4)[0] - 20 * mm) / max(1, len(frame.columns)))] * max(1, len(frame.columns))
        table = LongTable(data, colWidths=widths, repeatRows=1)
        table.setStyle([
            ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1FB")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D3E0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
        story.extend([Spacer(1, 4 * mm), table])
        if index < len(items) - 1:
            story.append(PageBreak())
    doc.build(story)


def export_dataframes(items: list[dict], export_format: str, filepath: str) -> dict:
    """Write selected data frames and return final path plus exported names."""
    if not items:
        raise ValueError("暂无可导出的数据")
    fmt = str(export_format or "xlsx").lower().lstrip(".")
    if fmt not in {"xlsx", "csv", "pdf"}:
        raise ValueError("仅支持 xlsx、csv 或 pdf 格式")
    target = Path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target.with_suffix(f".{fmt}")

    if fmt == "xlsx":
        used_names: set[str] = set()
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            for item in items:
                sheet = _make_sheet_name(item["name"], used_names)
                item["dataframe"].to_excel(writer, sheet_name=sheet, index=False)
                writer.book[sheet].sheet_state = "visible"
            _remove_default_sheet_if_safe(writer.book)
            _ensure_visible_workbook(writer.book)
    elif fmt == "csv" and len(items) == 1:
        items[0]["dataframe"].to_csv(target, index=False, encoding="utf-8-sig")
    elif fmt == "csv":
        target = target.with_suffix(".zip")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in items:
                csv_name = f"{_safe_stem(item['name'])}.csv"
                archive.writestr(csv_name, item["dataframe"].to_csv(index=False), compress_type=zipfile.ZIP_DEFLATED)
    else:
        _write_pdf(items, str(target))

    return {"filepath": str(target), "format": fmt, "exported_names": [item["name"] for item in items]}
