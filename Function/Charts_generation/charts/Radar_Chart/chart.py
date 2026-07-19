"""
雷达图 Radar Chart
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


def _close_loop(labels, values):
    if not labels or not values:
        return labels, values
    return labels + [labels[0]], values + [values[0]]


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
    title = options.get("title", "雷达图")
    color_scheme = options.get("color_scheme", "mckinsey")
    label_col = mapping.get("label") or mapping.get("x")
    value_col = mapping.get("value") or mapping.get("y")
    series_col = mapping.get("series")
    if not label_col or label_col not in df.columns:
        label_col = next((c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), df.columns[0])
    if not value_col or value_col not in df.columns:
        value_col = next((c for c in df.columns if c != label_col and pd.api.types.is_numeric_dtype(df[c])), None)
    if not value_col:
        return ChartResult(warnings=["雷达图需要维度字段和数值字段"])

    df_plot = df[[c for c in [label_col, value_col, series_col] if c and c in df.columns]].copy()
    df_plot[value_col] = pd.to_numeric(df_plot[value_col], errors="coerce")
    df_plot = df_plot.dropna(subset=[label_col, value_col])
    if df_plot.empty:
        return ChartResult(warnings=["无有效数据"])

    fig = go.Figure()
    if series_col and series_col in df_plot.columns:
        groups = list(df_plot[series_col].astype(str).unique())
        colors = get_colors_list(color_scheme, len(groups))
        for idx, group in enumerate(groups):
            gdf = df_plot[df_plot[series_col].astype(str) == group]
            labels = gdf[label_col].astype(str).tolist()
            values = gdf[value_col].astype(float).tolist()
            labels, values = _close_loop(labels, values)
            fig.add_trace(go.Scatterpolar(r=values, theta=labels, fill='toself', name=group, line=dict(color=colors[idx], width=2.5)))
    else:
        labels = df_plot[label_col].astype(str).tolist()
        values = df_plot[value_col].astype(float).tolist()
        labels, values = _close_loop(labels, values)
        color = get_colors_list(color_scheme, 1)[0]
        fig.add_trace(go.Scatterpolar(r=values, theta=labels, fill='toself', name=value_col, line=dict(color=color, width=2.5)))

    fig.update_layout(
        title=dict(text=title, x=0.02),
        paper_bgcolor='white',
        font=dict(family='Heiti SC, Microsoft YaHei, sans-serif', size=12),
        margin=dict(l=50, r=50, t=70, b=50),
        polar=dict(radialaxis=dict(visible=True, gridcolor='#E6E9EF'), bgcolor='white'),
        legend=dict(orientation='h', y=1.02, x=0),
    )
    html = _build_html(title, pio.to_html(fig, full_html=False, include_plotlyjs=False))
    return ChartResult(html=html, meta={"chart_id": "radar_chart", "label_col": label_col, "value_col": value_col, "series_col": series_col})
