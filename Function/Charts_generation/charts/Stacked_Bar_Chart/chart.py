"""
堆叠柱状图 Stacked Bar - 比较图表
图表分类: 比较 Comparison
感知排名: ★★★★☆

统一接口:
    generate(df, mapping, options) -> ChartResult
"""
import logging
log = logging.getLogger(__name__)
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
from charts.color_schemes import get_colors_list

__all__ = ["generate"]

_DATA_FMT = "x列(类别) + 分组列 + y列(数值) 或 宽格式(行标签 + 多个数值列)"
_DESC = "多个分组堆叠在同一柱内，适合比较组成与整体。支持宽格式自动转换，并可按百分比归一化。"


def _auto_col(df: pd.DataFrame, *hints: str) -> Optional[str]:
    strs = [c for c in df.columns if df[c].dtype == object or df[c].dtype == 'string']
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    col_lower = {str(c).lower(): c for c in df.columns}
    hints = tuple(h for h in hints if isinstance(h, str) and h)

    for h in hints:
        h_lower = h.lower()
        if h_lower in col_lower:
            return col_lower[h_lower]

    for h in hints:
        h_lower = h.lower()
        if len(h_lower) < 2:
            continue
        for col in df.columns:
            col_name = str(col).lower()
            if len(col_name) >= 2 and (h_lower in col_name or col_name in h_lower):
                return col

    if hints:
        hint = hints[0].lower()
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


def _detect_wide_format(df: pd.DataFrame, mapping: dict) -> bool:
    if mapping.get("value_cols") or isinstance(mapping.get("y"), list) or isinstance(mapping.get("series"), list):
        return True
    series_hint = mapping.get("series") or mapping.get("color")
    if isinstance(series_hint, str) and series_hint in df.columns:
        return False
    strs = [c for c in df.columns if df[c].dtype == object or df[c].dtype == 'string']
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return len(strs) == 1 and len(nums) >= 2


def _convert_wide_to_long(df: pd.DataFrame, id_col: str, value_cols=None) -> pd.DataFrame:
    if value_cols is None:
        value_cols = [c for c in df.columns if c != id_col and pd.api.types.is_numeric_dtype(df[c])]
    return df.melt(id_vars=[id_col], value_vars=value_cols, var_name="分类", value_name="数值")


def _build_html(title: str, chart_name: str, library: str, data_fmt: str, desc: str, embed: str) -> str:
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


def generate(df=None, mapping: Dict[str, str] = None, options: Dict[str, Any] = None,
             excel_path: str = None, x: str = "x", y: str = "y", color: str = "color",
             title: str = "堆叠柱状图", **kwargs) -> ChartResult:
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

    x_col = mapping.get("x") or x
    y_col = mapping.get("y") or y
    color_col = mapping.get("color") or mapping.get("series") or color
    title = options.get("title", title)
    color_scheme_name = options.get("color_scheme", "mckinsey")
    normalize_to_percentage = bool(options.get("normalize_to_percentage", False))

    if _detect_wide_format(df, mapping):
        string_cols = [c for c in df.columns if df[c].dtype == object or df[c].dtype == 'string']
        id_col = x_col if isinstance(x_col, str) and x_col in df.columns else (string_cols[0] if string_cols else df.columns[0])
        value_cols = mapping.get("value_cols")
        if not value_cols and isinstance(mapping.get("y"), list):
            value_cols = mapping["y"]
        if not value_cols and isinstance(mapping.get("series"), list):
            value_cols = mapping["series"]
        if value_cols:
            value_cols = [c for c in value_cols if c in df.columns and c != id_col]
        df = _convert_wide_to_long(df, id_col, value_cols or None)
        _x, _y, _color = id_col, "数值", "分类"
        warnings.append(f"自动转换宽格式数据：{id_col} (x) × 分类 (stack) × 数值 (y)")
    else:
        _x = _auto_col(df, x_col, "x", "类别", "category")
        _y = _auto_col(df, y_col, "y", "数值", "value", "amount", "count")
        if isinstance(color_col, str) and color_col in df.columns:
            _color = color_col
        else:
            _color = _auto_col(df, color_col, "series", "group", "分类", "category")

    if _x is None or _x not in df.columns:
        return ChartResult(warnings=["找不到必填字段 [x]"])
    if _y is None or _y not in df.columns:
        return ChartResult(warnings=["找不到必填字段 [y]"])
    if _color and _color not in df.columns:
        _color = None

    df_plot = df.copy()
    df_plot[_y] = pd.to_numeric(df_plot[_y], errors='coerce')
    df_plot = df_plot.dropna(subset=[_x, _y])
    if df_plot.empty:
        return ChartResult(warnings=["无有效数据"])

    if normalize_to_percentage and _color:
        totals = df_plot.groupby(_x)[_y].transform('sum').replace(0, pd.NA)
        df_plot[_y] = (df_plot[_y] / totals).fillna(0)

    palette = get_colors_list(color_scheme_name, max(df_plot[_color].nunique() if _color else 1, 10))
    fig = px.bar(
        df_plot,
        x=_x,
        y=_y,
        color=_color,
        title=title,
        barmode='stack',
        text_auto='.1%' if normalize_to_percentage else '.2f',
        color_discrete_sequence=palette,
        **kwargs,
    )
    fig.update_layout(
        font_family='Heiti SC, Microsoft YaHei, sans-serif',
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis_title=_x,
        yaxis_title=_y,
        legend_title=_color if _color else '',
    )
    fig.update_xaxes(showgrid=False, linecolor='#D9D9D9')
    fig.update_yaxes(showgrid=True, gridcolor='#E6E9EF', zeroline=False)
    if normalize_to_percentage:
        fig.update_yaxes(tickformat='.0%')

    chart_html = pio.to_html(fig, full_html=False, include_plotlyjs=False)
    html = _build_html(title, 'stacked_bar', 'plotly', _DATA_FMT, _DESC, chart_html)
    meta = {"chart_id": "stacked_bar", "n_rows": len(df_plot), "x_col": _x, "y_col": _y, "color_col": _color}
    return ChartResult(html=html, spec={}, warnings=warnings, meta=meta)
