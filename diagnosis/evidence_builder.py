from __future__ import annotations

from typing import Any

from domain.ecommerce_metrics import format_metric


def metric_evidence(metric: str, current: Any, previous: Any, change: Any, formula: str = "") -> dict[str, Any]:
    return {
        "metric": metric,
        "current": current,
        "previous": previous,
        "change": change,
        "formula": formula,
    }


def product_evidence(product: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "product_id": product.get("product_id"),
        "product_name": product.get("product_name") or product.get("product_id"),
        "reason": reason,
        "values": product,
    }


def action(priority: str, suggestion: str, basis: str, verification: str) -> str:
    return f"优先级：{priority}\n建议：{suggestion}\n依据：{basis}\n建议验证：{verification}"


def human_change(change: float | None) -> str:
    if change is None:
        return "无可比数据"
    return f"{change * 100:.2f}%"


def confidence_score(
    *,
    data_completeness: float,
    coverage: float,
    sample_size: int,
    match_strength: float,
) -> float:
    sample_component = min(1.0, max(0, sample_size) / 200)
    score = (
        data_completeness * 0.30
        + coverage * 0.25
        + sample_component * 0.20
        + match_strength * 0.25
    )
    return round(max(0.1, min(0.98, score)), 2)

