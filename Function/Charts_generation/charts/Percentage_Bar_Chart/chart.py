"""
占比条形图 Percentage Bar Chart
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
    title = options.get("title", "占比条形图")
    color_scheme = options.get("color_scheme", "mckinsey")
    label_col = mapping.get("label") or mapping.get("x")
    value_col = mapping.get("value") or mapping.get("y")
    if not label_col or label_col not in df.columns:
        label_col = next((c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), df.columns[0])
    if not value_col or value_col not in df.columns:
        value_col = next((c for c in df.columns if c != label_col and pd.api.types.is_numeric_dtype(df[c])), None)
    if not value_col:
        return ChartResult(warnings=["占比条形图需要一个类别字段和一个数值字段"])

    df_plot = df[[label_col, value_col]].copy()
    df_plot[value_col] = pd.to_numeric(df_plot[value_col], errors="coerce")
    df_plot = df_plot.dropna(subset=[label_col, value_col])
    if df_plot.empty:
        return ChartResult(warnings=["无有效数据"])

    vals = df_plot[value_col].astype(float)
    if vals.max() <= 1.0:
        df_plot["__pct__"] = vals
    elif vals.max() <= 100.0 and "%" in value_col:
        df_plot["__pct__"] = vals / 100.0
    else:
        total = vals.sum()
        if total == 0:
            return ChartResult(warnings=["占比总和为 0，无法生成图表"])
        df_plot["__pct__"] = vals / total

    df_plot = df_plot.sort_values("__pct__", ascending=False)
    colors = get_colors_list(color_scheme, len(df_plot))
    fig = go.Figure(go.Bar(
        x=df_plot["__pct__"],
        y=df_plot[label_col].astype(str),
        orientation="h",
        marker=dict(color=colors),
        text=[f"{v:.1%}" for v in df_plot["__pct__"]],
        textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>{value_col}: %{{x:.1%}}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, x=0.02),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Heiti SC, Microsoft YaHei, sans-serif", size=12),
        margin=dict(l=90, r=40, t=70, b=50),
        showlegend=False,
    )
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor="#E6E9EF")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    html = _build_html(title, pio.to_html(fig, full_html=False, include_plotlyjs=False))
    return ChartResult(html=html, meta={"chart_id": "percentage_bar_chart", "label_col": label_col, "value_col": value_col})
