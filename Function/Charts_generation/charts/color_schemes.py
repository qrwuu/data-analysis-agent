# -*- coding: utf-8 -*-
"""
配色方案管理模块
支持多种企业配色方案，并提供统一的数据分析图表调色板。
"""

ANALYTICS_COLORS = [
    "#6366F1",
    "#22C55E",
    "#F59E0B",
    "#EF4444",
    "#06B6D4",
    "#A855F7",
    "#84CC16",
    "#F97316",
    "#14B8A6",
    "#EC4899",
]

ANALYTICS_HEATMAP_SCALE = [
    [0.0, "#EEF2FF"],
    [0.2, "#C7D2FE"],
    [0.4, "#A5B4FC"],
    [0.6, "#818CF8"],
    [0.8, "#6366F1"],
    [1.0, "#4338CA"],
]

ANALYTICS_DIVERGING_SCALE = [
    [0.0, "#EF4444"],
    [0.2, "#FCA5A5"],
    [0.5, "#F8FAFC"],
    [0.8, "#93C5FD"],
    [1.0, "#6366F1"],
]

COLOR_SCHEMES = {
    "mckinsey": {
        "name": "Analytics Indigo",
        "description": "适合分析产品的蓝紫协调配色",
        "colors": ANALYTICS_COLORS,
        "primary": "#6366F1",
        "secondary": "#06B6D4",
        "accent": "#A855F7",
        "positive": "#22C55E",
        "negative": "#EF4444",
        "neutral": "#F59E0B",
        "heatmap_scale": ANALYTICS_HEATMAP_SCALE,
        "diverging_scale": ANALYTICS_DIVERGING_SCALE,
    },
    "product_analytics": {
        "name": "Product Analytics",
        "description": "统一的数据分析产品图表调色板",
        "colors": ANALYTICS_COLORS,
        "primary": "#6366F1",
        "secondary": "#06B6D4",
        "accent": "#A855F7",
        "positive": "#22C55E",
        "negative": "#EF4444",
        "neutral": "#F59E0B",
        "heatmap_scale": ANALYTICS_HEATMAP_SCALE,
        "diverging_scale": ANALYTICS_DIVERGING_SCALE,
    },
    "bcg": {
        "name": "BCG Green",
        "description": "波士顿咨询绿色配色",
        "colors": [
            "#006C5B",
            "#009879",
            "#00B398",
            "#CDECE5",
            "#EAF6F3",
            "#FFFFFF",
        ],
        "primary": "#006C5B",
        "secondary": "#009879",
        "accent": "#00B398",
        "positive": "#00B398",
        "negative": "#A6192E",
        "neutral": "#999999",
    },
    "bain": {
        "name": "Bain Red",
        "description": "贝恩红色配色",
        "colors": [
            "#E41E26",
            "#FF5C5C",
            "#A6192E",
            "#F4E8E9",
            "#EDEDED",
            "#FFFFFF",
            "#999999",
        ],
        "primary": "#E41E26",
        "secondary": "#FF5C5C",
        "accent": "#A6192E",
        "positive": "#00B398",
        "negative": "#E41E26",
        "neutral": "#999999",
    },
    "ey": {
        "name": "EY Yellow",
        "description": "安永黄色配色",
        "colors": [
            "#FFD100",
            "#FFED70",
            "#75787B",
            "#D9D9D6",
            "#BDBDBD",
            "#FFFFFF",
        ],
        "primary": "#FFD100",
        "secondary": "#FFED70",
        "accent": "#75787B",
        "positive": "#7FBA00",
        "negative": "#DA3B01",
        "neutral": "#75787B",
    },
}


def get_color_scheme(scheme_name):
    """
    获取指定配色方案
    """
    return COLOR_SCHEMES.get(scheme_name, COLOR_SCHEMES["mckinsey"])


def list_color_schemes():
    """
    获取所有可用的配色方案列表
    """
    return [
        {
            "scheme_id": scheme_id,
            "name": scheme["name"],
            "description": scheme["description"],
            "primary_color": scheme["primary"],
        }
        for scheme_id, scheme in COLOR_SCHEMES.items()
    ]


def get_colors_list(scheme_name, count=None):
    """
    获取指定配色方案的颜色列表
    """
    scheme = get_color_scheme(scheme_name)
    colors = scheme.get("colors", [])

    if count is None:
        return colors

    result = []
    for i in range(count):
        result.append(colors[i % len(colors)])
    return result


def get_heatmap_scale(scheme_name):
    """
    获取热力图渐变色。
    """
    scheme = get_color_scheme(scheme_name)
    return scheme.get("heatmap_scale", ANALYTICS_HEATMAP_SCALE)


def get_diverging_scale(scheme_name):
    """
    获取适合相关性/正负值热力图的发散色。
    """
    scheme = get_color_scheme(scheme_name)
    return scheme.get("diverging_scale", ANALYTICS_DIVERGING_SCALE)
