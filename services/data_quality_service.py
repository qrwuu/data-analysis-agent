from __future__ import annotations

from typing import Any

import pandas as pd

from models.diagnosis_result import QualityIssue
from services.comparison_service import infer_periods
from services.schema_mapper import REQUIRED_FIELDS


MONEY_FIELDS = {"payment_amount", "refund_amount", "ad_spend", "ad_revenue"}
NUMERIC_FIELDS = {
    "quantity",
    "payment_amount",
    "refund_amount",
    "impressions",
    "clicks",
    "visitors",
    "add_to_cart_users",
    "payment_buyers",
    "ad_spend",
    "ad_orders",
    "ad_revenue",
}


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _issue(severity: str, issue_type: str, fields: list[str], rows: int, total: int, risk: str, suggestion: str, auto_fixed: bool = False) -> QualityIssue:
    return QualityIssue(
        severity=severity,
        issue_type=issue_type,
        fields=fields,
        affected_rows=int(rows),
        affected_ratio=_ratio(int(rows), int(total)),
        risk=risk,
        suggestion=suggestion,
        auto_fixed=auto_fixed,
    )


def check_single_table(role: str, df: pd.DataFrame) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    total = len(df)
    required = REQUIRED_FIELDS.get(role, set())
    missing = [field for field in sorted(required) if field not in df.columns]
    if missing:
        issues.append(_issue(
            "critical",
            "missing_required_fields",
            missing,
            total,
            total,
            "必填字段缺失，无法按统一口径计算相关指标。",
            "请在字段映射中补充这些字段，或重新上传包含字段的数据。",
        ))
        return issues

    if "date" in df.columns:
        invalid_dates = pd.to_datetime(df["date"], errors="coerce").isna()
        count = int(invalid_dates.sum())
        if count:
            issues.append(_issue(
                "critical",
                "invalid_date",
                ["date"],
                count,
                total,
                "日期无法解析会导致周期对比和趋势图失真。",
                "请将日期统一为 YYYY-MM-DD 或 Excel 可识别日期格式。",
            ))

    for field in sorted(NUMERIC_FIELDS.intersection(df.columns)):
        numeric = pd.to_numeric(df[field], errors="coerce")
        invalid = numeric.isna() & df[field].notna()
        count = int(invalid.sum())
        if count:
            issues.append(_issue(
                "critical" if field in MONEY_FIELDS else "warning",
                "non_numeric_value",
                [field],
                count,
                total,
                "数值字段包含非数字内容，指标计算会跳过或归零这些记录。",
                "请清理文本、货币符号或异常字符后重新上传。",
            ))
        negative = numeric.fillna(0) < 0
        neg_count = int(negative.sum())
        if neg_count:
            issues.append(_issue(
                "warning",
                "negative_numeric_value",
                [field],
                neg_count,
                total,
                "负数金额或数量可能代表退款、冲销或录入错误，会影响经营判断。",
                "请确认负数是否符合业务含义；否则修正后重新分析。",
            ))

    if role == "orders":
        if "order_id" in df.columns:
            dup = df["order_id"].astype(str).duplicated(keep=False)
            count = int(dup.sum())
            if count:
                issues.append(_issue(
                    "warning",
                    "duplicate_order_id",
                    ["order_id"],
                    count,
                    total,
                    "重复订单会导致 GMV、订单数和退款金额被高估。",
                    "本次指标计算会按订单编号去重并保留最新一条记录。",
                    auto_fixed=True,
                ))
        if "product_id" in df.columns:
            empty_product = df["product_id"].isna() | df["product_id"].astype(str).str.strip().eq("")
            count = int(empty_product.sum())
            if count:
                issues.append(_issue("critical", "empty_product_id", ["product_id"], count, total, "商品ID为空会导致跨表关联失败。", "请补全商品ID后重新上传。"))
        if {"payment_amount", "refund_amount"}.issubset(df.columns):
            pay = pd.to_numeric(df["payment_amount"], errors="coerce").fillna(0)
            refund = pd.to_numeric(df["refund_amount"], errors="coerce").fillna(0)
            count = int((refund > pay).sum())
            if count:
                issues.append(_issue("warning", "refund_gt_payment", ["payment_amount", "refund_amount"], count, total, "退款金额大于支付金额会拉低净销售额并夸大退款风险。", "请核对退款记录是否重复或口径不一致。"))
        if {"payment_amount", "order_status"}.issubset(df.columns):
            pay = pd.to_numeric(df["payment_amount"], errors="coerce").fillna(0)
            status = df["order_status"].astype(str).str.strip()
            completed = status.isin({"completed", "shipped", "已完成", "已发货", "交易成功"})
            count = int(((pay == 0) & completed).sum())
            if count:
                issues.append(_issue("warning", "zero_payment_completed", ["payment_amount", "order_status"], count, total, "已完成订单支付金额为0，可能低估GMV。", "请确认是否为赠品、补发或异常订单。"))

    for field in df.columns:
        null_count = int(df[field].isna().sum())
        if total and null_count / total >= 0.3:
            issues.append(_issue("warning", "high_null_ratio", [str(field)], null_count, total, "字段空值比例较高，相关维度分析可能不稳定。", "请确认该字段是否应该补齐或从分析中剔除。"))

    if total < 20:
        issues.append(_issue("warning", "insufficient_rows", [], total, total, "样本量较少，异常判断的可信度会降低。", "建议上传至少两个完整周期的数据。"))

    for field in sorted(NUMERIC_FIELDS.intersection(df.columns)):
        numeric = pd.to_numeric(df[field], errors="coerce").dropna()
        if len(numeric) < 8:
            continue
        q1 = numeric.quantile(0.25)
        q3 = numeric.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        outliers = (numeric < q1 - 3 * iqr) | (numeric > q3 + 3 * iqr)
        count = int(outliers.sum())
        if count:
            issues.append(_issue("info", "extreme_outlier", [field], count, total, "极端值会影响均值、总额和趋势判断。", "建议核对这些记录是否为真实大促、异常退款或录入错误。"))

    return issues


def _date_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if df is None or df.empty or "date" not in df.columns:
        return None, None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return None, None
    return dates.min(), dates.max()


def _coverage(left: pd.Series, right: pd.Series) -> float:
    left_ids = set(left.dropna().astype(str).str.strip()) - {""}
    right_ids = set(right.dropna().astype(str).str.strip()) - {""}
    if not left_ids:
        return 0.0
    return len(left_ids.intersection(right_ids)) / len(left_ids)


def check_cross_table(datasets: dict[str, pd.DataFrame]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    frames = [df for df in datasets.values() if df is not None and not df.empty]
    current, previous, has_previous = infer_periods(frames)
    if current and not has_previous:
        issues.append(_issue(
            "warning",
            "missing_comparison_period",
            ["date"],
            0,
            0,
            "缺少等长上一周期数据，本次不输出环比异常结论。",
            "请补充更早周期的数据，或仅查看当前经营状态。",
        ))

    bounds = {role: _date_bounds(df) for role, df in datasets.items()}
    valid_bounds = {role: pair for role, pair in bounds.items() if pair[0] is not None and pair[1] is not None}
    if len(valid_bounds) >= 2:
        starts = [pair[0] for pair in valid_bounds.values()]
        ends = [pair[1] for pair in valid_bounds.values()]
        if max(starts) > min(starts) or max(ends) > min(ends):
            issues.append(_issue(
                "warning",
                "date_range_mismatch",
                ["date"],
                0,
                0,
                "不同数据表日期范围不一致，跨表归因可能只覆盖部分周期。",
                "建议上传相同统计周期的订单、流量和推广数据。",
            ))

    orders = datasets.get("orders")
    traffic = datasets.get("traffic")
    ads = datasets.get("advertising")
    if orders is not None and traffic is not None and {"product_id"}.issubset(orders.columns) and {"product_id"}.issubset(traffic.columns):
        cov = _coverage(traffic["product_id"], orders["product_id"])
        if cov < 0.8:
            issues.append(_issue("warning", "traffic_order_product_coverage", ["product_id"], 0, 0, "流量表与订单表商品ID覆盖率不足，商品级转化归因可能不完整。", f"当前覆盖率 {cov:.1%}，请检查商品ID口径是否一致。"))
    if ads is not None and traffic is not None and {"product_id"}.issubset(ads.columns) and {"product_id"}.issubset(traffic.columns):
        cov = _coverage(ads["product_id"], traffic["product_id"])
        if cov < 0.8:
            issues.append(_issue("warning", "ad_traffic_product_coverage", ["product_id"], 0, 0, "推广表与流量表商品ID覆盖率不足，广告效果归因可能不完整。", f"当前覆盖率 {cov:.1%}，请检查商品ID口径是否一致。"))
    return issues


def run_quality_checks(datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    all_issues: list[QualityIssue] = []
    by_role: dict[str, list[dict[str, Any]]] = {}
    for role, df in datasets.items():
        role_issues = check_single_table(role, df)
        by_role[role] = [issue.to_dict() for issue in role_issues]
        all_issues.extend(role_issues)
    cross = check_cross_table(datasets)
    all_issues.extend(cross)
    blocks = [issue for issue in all_issues if issue.severity == "critical" and not issue.auto_fixed]
    return {
        "issues": [issue.to_dict() for issue in all_issues],
        "by_role": by_role,
        "blocking": bool(blocks),
        "blocking_reasons": [issue.risk for issue in blocks],
    }

