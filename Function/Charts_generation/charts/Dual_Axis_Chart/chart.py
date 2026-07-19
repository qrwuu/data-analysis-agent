"""
双轴图 Dual Axis Chart
"""
import logging
log = logging.getLogger(__name__)
import sys
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from charts.base import ChartResult
from charts.color_schemes import get_colors_list

_DATA_FMT = "x列 + 两个或多个数值列"
_DESC = "使用左右双轴展示不同量纲的指标，如销售额与订单数。默认第一条为柱状，第二条及之后为折线。"


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
    title = options.get("title", "双轴图")
    color_scheme = options.get("color_scheme", "mckinsey")
    x_col = mapping.get("x")
    y_cols = mapping.get("y") or mapping.get("value_cols") or []
    if isinstance(y_cols, str):
        y_cols = [y_cols]
    y_cols = [str(c) for c in y_cols if str(c) in df.columns]

    if not x_col or x_col not in df.columns:
        x_col = next((c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), df.columns[0])
    if len(y_cols) < 2:
        y_cols = [c for c in df.columns if c != x_col and pd.api.types.is_numeric_dtype(df[c])][:3]
    if len(y_cols) < 2:
        return ChartResult(warnings=["双轴图至少需要两个数值字段"])

    df_plot = df[[x_col] + y_cols].copy()
    for col in y_cols:
        df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")
    df_plot = df_plot.dropna(subset=y_cols, how="all")
    if df_plot.empty:
        return ChartResult(warnings=["无有效数据"])

    colors = get_colors_list(color_scheme, len(y_cols) + 2)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df_plot[x_col].astype(str),
            y=df_plot[y_cols[0]],
            name=y_cols[0],
            marker_color=colors[0],
            hovertemplate=f"<b>%{{x}}</b><br>{y_cols[0]}: %{{y:,.2f}}<extra></extra>",
        ),
        secondary_y=False,
    )
    for idx, col in enumerate(y_cols[1:], start=1):
        fig.add_trace(
            go.Scatter(
                x=df_plot[x_col].astype(str),
                y=df_plot[col],
                mode="lines+markers",
                name=col,
                line=dict(color=colors[idx], width=3),
                marker=dict(color=colors[idx], size=7),
                hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,.2f}}<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title=dict(text=title, x=0.02),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Heiti SC, Microsoft YaHei, sans-serif", size=12),
        margin=dict(l=60, r=60, t=70, b=60),
        legend=dict(orientation="h", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor="#D9D9D9")
    fig.update_yaxes(title_text=y_cols[0], secondary_y=False, showgrid=True, gridcolor="#E6E9EF")
    fig.update_yaxes(title_text=" / ".join(y_cols[1:]), secondary_y=True, showgrid=False)

    html = _build_html(title, pio.to_html(fig, full_html=False, include_plotlyjs=False))
    return ChartResult(html=html, meta={"chart_id": "dual_axis_chart", "x_col": x_col, "y_cols": y_cols})
