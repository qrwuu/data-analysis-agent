"""
漏斗图 Funnel Chart
"""
import logging
log = logging.getLogger(__name__)
import sys
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from charts.base import ChartResult
from charts.color_schemes import get_colors_list


def _build_html(title: str, embed: str) -> str:
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{title}</title></head><body><div class="chart-wrap"><h1>{title}</h1>{embed}</div></body></html>"""


def generate(df=None, mapping: Dict[str, Any] = None, options: Dict[str, Any] = None, excel_path: str = None, **kwargs):
    options = options or {}
    mapping = mapping or {}
    if df is None:
        if excel_path:
            df = pd.read_excel(excel_path)
        else:
            return ChartResult(warnings=["请提供 df 或 excel_path"])

    df = df.copy()
    df.columns = df.columns.map(str)
    title = options.get("title", "漏斗图")
    color_scheme = options.get("color_scheme", "mckinsey")
    x_col = mapping.get("x") or mapping.get("label")
    y_col = mapping.get("y") or mapping.get("value")
    if not x_col or x_col not in df.columns:
        x_col = next((c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), df.columns[0])
    if not y_col or y_col not in df.columns:
        y_col = next((c for c in df.columns if c != x_col and pd.api.types.is_numeric_dtype(df[c])), None)
    if not y_col:
        return ChartResult(warnings=["漏斗图需要阶段字段和数值字段"])

    df_plot = df[[x_col, y_col]].copy()
    df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors="coerce")
    df_plot = df_plot.dropna(subset=[x_col, y_col]).sort_values(y_col, ascending=False)
    if df_plot.empty:
        return ChartResult(warnings=["无有效数据"])

    colors = get_colors_list(color_scheme, len(df_plot))
    fig = go.Figure(go.Funnel(
        y=df_plot[x_col].astype(str),
        x=df_plot[y_col],
        textinfo="value+percent previous",
        marker=dict(color=colors),
        hovertemplate=f"<b>%{{y}}</b><br>{y_col}: %{{x:,.2f}}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, x=0.02),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Heiti SC, Microsoft YaHei, sans-serif", size=12),
        margin=dict(l=70, r=40, t=70, b=50),
    )
    html = _build_html(title, pio.to_html(fig, full_html=False, include_plotlyjs=False))
    return ChartResult(html=html, meta={"chart_id": "funnel_chart", "x_col": x_col, "y_col": y_col})
