"""
柱状图 Bar Chart - 比较图表
图表分类: 比较 Comparisons | 书章节: Ch4
感知排名: ★★★★★
"""
import logging
log = logging.getLogger(__name__)
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
import plotly.express as px
import plotly.io as pio

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from charts.base import ChartResult
from charts.color_schemes import get_color_scheme, get_colors_list

__all__ = ["generate"]

FONT_PATH = os.environ.get("CHARTS_FONT_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "AlibabaPuHuiTi-3-55-Regular.ttf"
)

_DATA_FMT = "x列(类别) + y列(数值)"
_DESC = "通过矩形高度编码数值，适合对比、排名和 Top N 分析。支持横向柱状图与多色类别展示。"


def _auto_col(df: pd.DataFrame, *hints: str) -> Optional[str]:
    strs = [
        c for c in df.columns if df[c].dtype == object
        or str(df[c].dtype).startswith('string')
        or pd.api.types.is_string_dtype(df[c])
    ]
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    col_lower = {str(c).lower(): c for c in df.columns}

    for h in hints:
        if h is None:
            continue
        h_lower = str(h).lower()
        if h_lower in col_lower:
            return col_lower[h_lower]

    for h in hints:
        if h is None:
            continue
        h_lower = str(h).lower()
        if len(h_lower) < 2:
            continue
        for col in df.columns:
            col_name = str(col).lower()
            if len(col_name) >= 2 and (h_lower in col_name or col_name in h_lower):
                return col

    if hints and hints[0] is not None:
        hint = str(hints[0]).lower()
        if any(kw in hint for kw in ["label", "name", "group", "category", "x", "类别"]):
            if strs:
                return strs[0]
            if nums:
                return nums[0]
        if any(kw in hint for kw in ["value", "amount", "count", "score", "y", "数值", "金额"]):
            if nums:
                return nums[0]
            if strs:
                return strs[0]

    if strs:
        return strs[0]
    if nums:
        return nums[0]
    return None


def _build_html(title: str, chart_name: str, library: str,
                data_fmt: str, desc: str, embed: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>{title}</title>
<style>
body{{font-family:"Heiti SC","Microsoft YaHei",sans-serif;margin:40px;background:#fafafa}}
.chart-wrap{{background:white;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);padding:24px;margin-bottom:32px}}
h1{{color:#222;font-size:22px;margin-bottom:6px}}
.subtitle{{color:#888;font-size:13px;margin-bottom:24px}}
.desc{{color:#555;font-size:14px;line-height:1.7;margin-top:20px}}
</style></head>
<body><div class="chart-wrap">
<h1>{title}</h1><div class="subtitle">{chart_name} | {library}</div>
{embed}
</div><div class="desc">
<strong>数据格式：</strong>{data_fmt}<br>
<strong>说明：</strong>{desc}
</div></body></html>"""


def generate(
    df: pd.DataFrame = None,
    mapping: Dict[str, str] = None,
    options: Dict[str, Any] = None,
    excel_path: str = None,
    x: str = "x",
    y: str = "y",
    orientation: str = "v",
    title: str = "柱状图",
    color: str = "#4C78A8",
    sort: bool = True,
    top_n: int = None,
    **kwargs
) -> ChartResult:
    warnings: list = []
    options = options or {}
    mapping = mapping or {}

    if df is None:
        if excel_path:
            try:
                df = pd.read_excel(excel_path)
            except Exception as e:
                log.warning("[chart] 图表生成异常: %s", e)
                return ChartResult(warnings=[f"读取Excel失败: {e}"])
        else:
            return ChartResult(warnings=["请提供 df 或 excel_path"])

    x_col = mapping.get("x") or mapping.get("label") or x
    y_col = mapping.get("y") or mapping.get("value") or y
    title = options.get("title", title)
    orientation = str(options.get("orientation", orientation) or "v").lower()
    sort = options.get("sort", sort)
    top_n = options.get("top_n", top_n)
    color_scheme_name = options.get("color_scheme", "mckinsey")

    orientation = "h" if orientation in {"h", "horizontal", "horizontal_bar"} else "v"
    scheme = get_color_scheme(color_scheme_name)
    colors = get_colors_list(color_scheme_name, max(len(df), 10))
    default_color = scheme.get("primary", color)

    _x = _auto_col(df, x_col, "x", "类别", "category", "label", "name")
    _y = _auto_col(df, y_col, "y", "数值", "value", "amount", "num", "count")

    if _x is None or _x not in df.columns:
        return ChartResult(warnings=["找不到必填字段 [x]"])
    if _y is None or _y not in df.columns:
        return ChartResult(warnings=["找不到必填字段 [y]"])

    df_plot = df[[_x, _y]].copy()
    df_plot[_y] = pd.to_numeric(df_plot[_y], errors='coerce')
    df_plot = df_plot.dropna(subset=[_x, _y])

    if df_plot.empty:
        return ChartResult(warnings=["数据为空"])

    if sort:
        df_plot = df_plot.sort_values(_y, ascending=False)
    if top_n:
        df_plot = df_plot.head(int(top_n))

    value_series = df_plot[_y].dropna()
    is_ratio = not value_series.empty and ((value_series >= 0) & (value_series <= 1)).mean() >= 0.8
    text_fmt = ".1%" if is_ratio else ".2f"

    category_count = df_plot[_x].nunique()
    use_multicolor = category_count > 1

    if orientation == "h":
        fig = px.bar(
            df_plot,
            x=_y,
            y=_x,
            color=_x if use_multicolor else None,
            orientation='h',
            title=title,
            color_discrete_sequence=colors if use_multicolor else [default_color],
            text_auto=text_fmt,
            **kwargs,
        )
        fig.update_yaxes(autorange="reversed")
    else:
        fig = px.bar(
            df_plot,
            x=_x,
            y=_y,
            color=_x if use_multicolor else None,
            orientation='v',
            title=title,
            color_discrete_sequence=colors if use_multicolor else [default_color],
            text_auto=text_fmt,
            **kwargs,
        )

    fig.update_traces(
        marker_line_width=0,
        hovertemplate=f"<b>%{{x}}</b><br>{_y}: %{{y:.2f}}<extra></extra>" if orientation == 'v'
        else f"<b>%{{y}}</b><br>{_y}: %{{x:.2f}}<extra></extra>",
    )
    fig.update_layout(
        font_family="Heiti SC, Microsoft YaHei, sans-serif",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=40, t=70, b=60),
        title_font_size=16,
        showlegend=False,
        hovermode="closest",
        xaxis_title=_x if orientation == 'v' else _y,
        yaxis_title=_y if orientation == 'v' else _x,
        bargap=max(0.12, min(0.28, 0.12 + category_count * 0.01)),
    )
    fig.update_xaxes(showgrid=False, linecolor="#D9D9D9")
    fig.update_yaxes(showgrid=True, gridcolor="#E6E9EF", zeroline=False)
    if is_ratio:
        if orientation == 'v':
            fig.update_yaxes(tickformat='.0%')
        else:
            fig.update_xaxes(tickformat='.0%')

    chart_html = pio.to_html(fig, full_html=False, include_plotlyjs=False)
    html = _build_html(title, "bar_chart", "plotly", _DATA_FMT, _DESC, chart_html)

    meta = {
        "chart_id": "bar_chart",
        "n_rows": len(df_plot),
        "x_col": _x,
        "y_col": _y,
        "orientation": orientation,
    }

    return ChartResult(html=html, spec={}, warnings=warnings, meta=meta)
