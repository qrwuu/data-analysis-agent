from __future__ import annotations

from typing import Any


def summarize_metrics(metric_context: dict[str, Any]) -> list[str]:
    cards = metric_context.get("cards") or []
    if not cards:
        return ["当前数据不足，无法生成核心经营指标。"]
    summary = []
    by_id = {item.get("metric_id"): item for item in cards}
    for key in ("paid_gmv", "net_sales", "payment_conversion_rate", "refund_rate", "roas"):
        item = by_id.get(key)
        if item:
            summary.append(f"{item.get('name')}：{item.get('formatted')}（{item.get('formula')}）")
    return summary

