"""Conservative natural-language routing for built-in analysis Skills.

The tool picker remains a useful shortcut, but it must not be required for a
user to access a capability.  This router only recognizes high-confidence
phrases and never overrides an explicit skill or slash-command selection.
"""
from __future__ import annotations

import re


# Specific workflows come before generic data / chart requests.  Keep these
# patterns product-facing: users should not have to know the implementation
# name of an analysis method to use it.
_SKILL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("winsorize", re.compile(r"winsori[sz]e|缩尾|极值缩尾", re.IGNORECASE)),
    ("trimming", re.compile(r"截尾|去除.*极端值|删除.*异常样本", re.IGNORECASE)),
    ("inset", re.compile(r"缺失值(?:的)?(?:填补|补全|插补|处理)|填补.*缺失值|补全.*缺失值|插补", re.IGNORECASE)),
    ("kmeans", re.compile(r"k\s*-?\s*means|聚类|分群|客户分成\s*\d+\s*类", re.IGNORECASE)),
    ("tree", re.compile(r"决策树|预测.*流失|流失.*预测|流失预警", re.IGNORECASE)),
    ("logistic", re.compile(r"逻辑回归|二分类|多分类|转化概率", re.IGNORECASE)),
    ("screening", re.compile(r"单变量筛选|变量筛选|筛选.*解释变量", re.IGNORECASE)),
    ("regression", re.compile(r"线性回归|回归分析|影响因素分析", re.IGNORECASE)),
    ("sarima", re.compile(r"\bsarima\b|季节性.*预测|季节性时间序列", re.IGNORECASE)),
    ("arima", re.compile(r"\barima\b|ARIMA", re.IGNORECASE)),
    ("prophet", re.compile(r"\bprophet\b", re.IGNORECASE)),
    ("gru", re.compile(r"\bgru\b|深度学习.*预测", re.IGNORECASE)),
    ("var", re.compile(r"\bvar\b|向量自回归|多个时间序列", re.IGNORECASE)),
    ("funnel-analysis", re.compile(r"漏斗分析|转化漏斗|转化率.*环节", re.IGNORECASE)),
    ("decile", re.compile(r"十等分|十分位|十分位数|客户分层", re.IGNORECASE)),
    ("dashboard", re.compile(r"仪表盘|数据看板|经营看板", re.IGNORECASE)),
    ("ppt", re.compile(r"生成.*(?:ppt|PPT|演示文稿)|(?:ppt|PPT).*汇报", re.IGNORECASE)),
    ("report", re.compile(r"生成.*(?:报告|report)|(?:报告|report).*导出", re.IGNORECASE)),
    ("export", re.compile(r"导出.*(?:excel|csv|xlsx|数据)|(?:excel|csv|xlsx).*导出", re.IGNORECASE)),
    ("data", re.compile(r"数据概况|数据质量|字段(?:情况|说明)|缺失情况|异常值", re.IGNORECASE)),
    ("sql", re.compile(r"\bsql\b|select\s+.+\s+from|查询.*(?:表|字段|前\d+行)", re.IGNORECASE)),
    ("chart", re.compile(r"图表|可视化|画图|绘图|趋势图|对比图|分布图|散点图|柱状图|折线图|饼图", re.IGNORECASE)),
)


def infer_builtin_skill(message: str) -> str:
    """Return one high-confidence built-in Skill name, or an empty string."""
    text = str(message or "").strip()
    if not text:
        return ""
    for skill_name, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            return skill_name
    return ""


def routable_skill_names() -> frozenset[str]:
    """Expose the supported set for contract tests and diagnostics."""
    return frozenset(skill_name for skill_name, _ in _SKILL_PATTERNS)
