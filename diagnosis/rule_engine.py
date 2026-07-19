from __future__ import annotations

from typing import Any

from diagnosis.evidence_builder import action, confidence_score, human_change, metric_evidence, product_evidence
from models.diagnosis_result import DiagnosisResult


def _change(context: dict[str, Any], key: str) -> float | None:
    return (context.get("changes") or {}).get(key, {}).get("change")


def _metric_value(context: dict[str, Any], bucket: str, key: str) -> Any:
    return (((context.get("metrics") or {}).get(bucket) or {}).get(key) or {}).get("value")


def _previous_value(context: dict[str, Any], bucket: str, key: str) -> Any:
    return (((context.get("previous_metrics") or {}).get(bucket) or {}).get(key) or {}).get("value")


def _rows(context: dict[str, Any], table: str) -> list[dict[str, Any]]:
    return list(((context.get("tables") or {}).get(table)) or [])


def _coverage_from_quality(quality: dict[str, Any]) -> float:
    issues = quality.get("issues") or []
    coverage_penalty = 0.0
    for issue in issues:
        if "coverage" in str(issue.get("issue_type") or ""):
            coverage_penalty += 0.2
    return max(0.4, 1.0 - coverage_penalty)


def _data_completeness(quality: dict[str, Any]) -> float:
    issues = quality.get("issues") or []
    penalty = 0.0
    for issue in issues:
        severity = issue.get("severity")
        if severity == "critical":
            penalty += 0.3
        elif severity == "warning":
            penalty += 0.08
    return max(0.35, 1.0 - penalty)


def _result(
    rule_id: str,
    title: str,
    severity: str,
    affected_metrics: list[str],
    current_value: Any,
    comparison_value: Any,
    change: Any,
    products: list[str],
    evidence: list[dict[str, Any]],
    possible_causes: list[str],
    recommendations: list[str],
    confidence: float,
) -> DiagnosisResult:
    return DiagnosisResult(
        title=title,
        severity=severity,
        affected_metrics=affected_metrics,
        current_value=current_value,
        comparison_value=comparison_value,
        change=change,
        products=products,
        rule_id=rule_id,
        evidence=evidence,
        possible_causes=possible_causes,
        recommendations=recommendations,
        confidence=confidence,
    )


def run_diagnosis(metric_context: dict[str, Any], quality: dict[str, Any] | None = None) -> list[DiagnosisResult]:
    quality = quality or {}
    if not metric_context.get("has_comparison"):
        comparison_allowed = False
    else:
        comparison_allowed = True
    completeness = _data_completeness(quality)
    coverage = _coverage_from_quality(quality)
    sample_size = sum(len(_rows(metric_context, table)) for table in ("product_orders", "product_traffic", "campaigns"))
    results: list[DiagnosisResult] = []

    gmv_change = _change(metric_context, "paid_gmv")
    visitors_change = _change(metric_context, "visitors")
    conversion_change = _change(metric_context, "payment_conversion_rate")
    if comparison_allowed and gmv_change is not None and visitors_change is not None and conversion_change is not None:
        if gmv_change < -0.20 and -0.05 <= visitors_change <= 0.05 and conversion_change < -0.15:
            strength = min(1.0, abs(gmv_change) / 0.35 + abs(conversion_change) / 0.35)
            results.append(_result(
                "R1",
                "转化承接异常",
                "high",
                ["支付GMV", "访客数", "支付转化率"],
                _metric_value(metric_context, "orders", "paid_gmv"),
                _previous_value(metric_context, "orders", "paid_gmv"),
                human_change(gmv_change),
                [],
                [
                    metric_evidence("支付GMV", _metric_value(metric_context, "orders", "paid_gmv"), _previous_value(metric_context, "orders", "paid_gmv"), human_change(gmv_change), "有效支付订单 payment_amount 求和"),
                    metric_evidence("访客数", _metric_value(metric_context, "traffic", "visitors"), _previous_value(metric_context, "traffic", "visitors"), human_change(visitors_change), "visitors 求和"),
                    metric_evidence("支付转化率", _metric_value(metric_context, "traffic", "payment_conversion_rate"), _previous_value(metric_context, "traffic", "payment_conversion_rate"), human_change(conversion_change), "payment_buyers / visitors"),
                ],
                ["价格、库存、优惠、评价或详情页承接下降", "支付链路或活动规则变化"],
                [action("高", "优先检查转化链路，不要只追加流量。", f"访客变化 {human_change(visitors_change)}，但支付转化率变化 {human_change(conversion_change)}。", "检查价格、库存、优惠、近7日评价和SKU可售状态。")],
                confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=strength),
            ))

    if comparison_allowed and visitors_change is not None and gmv_change is not None and conversion_change is not None:
        if visitors_change > 0.20 and gmv_change < 0.05 and conversion_change < -0.10:
            results.append(_result(
                "R2",
                "低质量流量",
                "medium",
                ["访客数", "支付GMV", "支付转化率"],
                _metric_value(metric_context, "traffic", "visitors"),
                _previous_value(metric_context, "traffic", "visitors"),
                human_change(visitors_change),
                [],
                [metric_evidence("访客数", _metric_value(metric_context, "traffic", "visitors"), _previous_value(metric_context, "traffic", "visitors"), human_change(visitors_change), "visitors 求和")],
                ["新增流量人群不精准", "商品承接不足或活动利益点不清晰"],
                [action("中", "拆分新增流量来源，暂停低转化来源扩量。", f"访客增长 {human_change(visitors_change)}，GMV增长 {human_change(gmv_change)}。", "按渠道、商品和人群查看转化率。")],
                confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.8),
            ))

    ad_spend_change = _change(metric_context, "ad_spend")
    ad_revenue_change = _change(metric_context, "ad_revenue")
    roas_change = _change(metric_context, "roas")
    if comparison_allowed and (
        (ad_spend_change is not None and ad_revenue_change is not None and ad_spend_change > 0.20 and ad_revenue_change < 0)
        or (roas_change is not None and roas_change < -0.20)
    ):
        results.append(_result(
            "R3",
            "推广效率恶化",
            "high",
            ["广告消耗", "广告成交金额", "广告ROAS"],
            _metric_value(metric_context, "advertising", "roas"),
            _previous_value(metric_context, "advertising", "roas"),
            human_change(roas_change),
            [],
            [
                metric_evidence("广告消耗", _metric_value(metric_context, "advertising", "ad_spend"), _previous_value(metric_context, "advertising", "ad_spend"), human_change(ad_spend_change), "ad_spend 求和"),
                metric_evidence("广告ROAS", _metric_value(metric_context, "advertising", "roas"), _previous_value(metric_context, "advertising", "roas"), human_change(roas_change), "ad_revenue / ad_spend"),
            ],
            ["投放人群变宽导致效率下降", "商品页转化或广告素材点击质量下降"],
            [action("高", "暂停扩大低 ROAS 计划预算，优先复盘素材和关键词。", f"ROAS变化 {human_change(roas_change)}。", "查看计划级 ROAS、CPC、转化率和商品承接。")],
            confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.9),
        ))

    product_traffic = _rows(metric_context, "product_traffic")
    if len(product_traffic) >= 4:
        sorted_visitors = sorted(product_traffic, key=lambda row: row.get("visitors") or 0, reverse=True)
        sorted_conversion = sorted(product_traffic, key=lambda row: row.get("payment_conversion_rate") if row.get("payment_conversion_rate") is not None else 999)
        top_count = max(1, int(len(product_traffic) * 0.25))
        high_traffic_ids = {str(row.get("product_id")) for row in sorted_visitors[:top_count]}
        low_conversion = [row for row in sorted_conversion[:top_count] if str(row.get("product_id")) in high_traffic_ids]
        for product in low_conversion[:3]:
            product_name = str(product.get("product_name") or product.get("product_id"))
            results.append(_result(
                "R4",
                "高流量低转化商品",
                "medium",
                ["访客数", "支付转化率"],
                product.get("payment_conversion_rate"),
                None,
                None,
                [product_name],
                [product_evidence(product, "访客数位于前25%，支付转化率位于后25%。")],
                ["主图、标题、价格或详情页承接不足", "流量人群与商品不匹配"],
                [action("中", f"优先优化 {product_name} 的商品页承接。", "该商品流量高但支付转化率低。", "检查主图点击承诺与详情页、价格、库存和评价一致性。")],
                confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.75),
            ))

    refund_rate = _metric_value(metric_context, "orders", "refund_rate")
    refund_rate_change = _change(metric_context, "refund_rate")
    if (refund_rate is not None and refund_rate > 0.15) or (comparison_allowed and refund_rate_change is not None and refund_rate_change > 0.02):
        results.append(_result(
            "R5",
            "退款风险",
            "high",
            ["金额退款率", "退款金额"],
            refund_rate,
            _previous_value(metric_context, "orders", "refund_rate"),
            human_change(refund_rate_change),
            [],
            [metric_evidence("金额退款率", refund_rate, _previous_value(metric_context, "orders", "refund_rate"), human_change(refund_rate_change), "退款金额 / 支付GMV")],
            ["商品质量、物流体验、描述不符或售后集中爆发"],
            [action("高", "优先排查退款金额最高的商品和退款原因。", "退款率超过阈值或较上期明显提升。", "按商品查看退款金额排行、近7日评价和售后原因。")],
            confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.85),
        ))

    product_orders = _rows(metric_context, "product_orders")
    total_gmv = _metric_value(metric_context, "orders", "paid_gmv") or 0
    if product_orders and total_gmv:
        top = max(product_orders, key=lambda row: row.get("paid_gmv") or 0)
        share = (top.get("paid_gmv") or 0) / total_gmv if total_gmv else 0
        if share > 0.60:
            product_name = str(top.get("product_name") or top.get("product_id"))
            results.append(_result(
                "R6",
                "商品依赖风险",
                "medium",
                ["支付GMV"],
                share,
                None,
                f"{share * 100:.2f}%",
                [product_name],
                [product_evidence(top, f"单一商品贡献GMV {share:.1%}。")],
                ["销售结构过度集中", "爆款波动会直接影响整体业绩"],
                [action("中", "降低单一商品依赖，建立第二梯队商品。", f"{product_name} 贡献GMV {share:.1%}。", "查看第二至第五名商品的流量、转化和库存，制定承接计划。")],
                confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.7),
            ))

    impressions_change = _change(metric_context, "impressions")
    ctr_change = _change(metric_context, "ctr")
    if comparison_allowed and impressions_change is not None and ctr_change is not None and impressions_change > 0 and ctr_change < -0.15:
        results.append(_result(
            "R7",
            "点击问题",
            "medium",
            ["曝光量", "点击率CTR"],
            _metric_value(metric_context, "traffic", "ctr"),
            _previous_value(metric_context, "traffic", "ctr"),
            human_change(ctr_change),
            [],
            [metric_evidence("点击率CTR", _metric_value(metric_context, "traffic", "ctr"), _previous_value(metric_context, "traffic", "ctr"), human_change(ctr_change), "clicks / impressions")],
            ["主图、标题、价格或人群匹配度不足"],
            [action("中", "优化曝光承接素材，先提升点击率再扩量。", f"曝光增长但CTR变化 {human_change(ctr_change)}。", "AB测试主图、标题、价格锚点和投放人群。")],
            confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.7),
        ))

    cart_change = _change(metric_context, "add_to_cart_users")
    buyers_change = _change(metric_context, "payment_buyers")
    if comparison_allowed and cart_change is not None and buyers_change is not None and cart_change >= -0.05 and buyers_change < -0.15:
        results.append(_result(
            "R8",
            "加购到支付流失",
            "medium",
            ["加购人数", "支付买家数"],
            _metric_value(metric_context, "traffic", "payment_buyers"),
            _previous_value(metric_context, "traffic", "payment_buyers"),
            human_change(buyers_change),
            [],
            [metric_evidence("加购人数", _metric_value(metric_context, "traffic", "add_to_cart_users"), _previous_value(metric_context, "traffic", "add_to_cart_users"), human_change(cart_change), "add_to_cart_users 求和")],
            ["价格、优惠、库存、运费或支付环节出现流失"],
            [action("中", "检查加购后的支付阻力，优先处理库存和优惠问题。", f"加购稳定但支付买家变化 {human_change(buyers_change)}。", "检查SKU库存、优惠门槛、运费和支付失败反馈。")],
            confidence_score(data_completeness=completeness, coverage=coverage, sample_size=sample_size, match_strength=0.75),
        ))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(results, key=lambda item: (severity_order.get(item.severity, 9), -item.confidence))

