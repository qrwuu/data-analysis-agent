from __future__ import annotations

from typing import Any

import pandas as pd

from domain.ecommerce_metrics import (
    campaign_metrics,
    compute_ad_metrics,
    compute_order_metrics,
    compute_traffic_metrics,
    daily_order_series,
    format_metric,
    product_order_metrics,
    product_traffic_metrics,
)
from services.comparison_service import infer_periods, pct_change


def _dict_metrics(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {key: value.to_dict() for key, value in metrics.items()}


def _records(df: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    cleaned = df.head(limit).copy()
    for col in cleaned.columns:
        if pd.api.types.is_float_dtype(cleaned[col]):
            cleaned[col] = cleaned[col].round(6)
    return cleaned.where(pd.notna(cleaned), None).to_dict(orient="records")


def _sort_if_present(df: pd.DataFrame, column: str, *, ascending: bool = True) -> pd.DataFrame:
    if df is None or df.empty or column not in df.columns:
        return df
    return df.sort_values(column, ascending=ascending, na_position="last")


def _merge_cards(order: dict, traffic: dict, ads: dict) -> list[dict[str, Any]]:
    wanted = [
        ("paid_gmv", order),
        ("net_sales", order),
        ("paid_orders", order),
        ("average_order_value", order),
        ("visitors", traffic),
        ("payment_conversion_rate", traffic),
        ("refund_rate", order),
        ("ad_spend", ads),
        ("roas", ads),
    ]
    cards = []
    for key, source in wanted:
        item = source.get(key)
        if item:
            cards.append(item.to_dict())
    return cards


def build_metric_context(
    datasets: dict[str, pd.DataFrame],
    *,
    current_period: dict[str, str] | None = None,
    comparison_period: dict[str, str] | None = None,
) -> dict[str, Any]:
    frames = [datasets.get("orders"), datasets.get("traffic"), datasets.get("advertising")]
    inferred_current, inferred_comparison, has_comparison = infer_periods([frame for frame in frames if frame is not None])
    current = current_period or inferred_current
    comparison = comparison_period or inferred_comparison

    orders = datasets.get("orders", pd.DataFrame())
    traffic = datasets.get("traffic", pd.DataFrame())
    advertising = datasets.get("advertising", pd.DataFrame())

    order_metrics = compute_order_metrics(orders, current)
    traffic_metrics = compute_traffic_metrics(traffic, current)
    ad_metrics = compute_ad_metrics(advertising, current)
    previous_order = compute_order_metrics(orders, comparison) if has_comparison else {}
    previous_traffic = compute_traffic_metrics(traffic, comparison) if has_comparison else {}
    previous_ads = compute_ad_metrics(advertising, comparison) if has_comparison else {}

    changes: dict[str, dict[str, Any]] = {}
    for bucket in (order_metrics, traffic_metrics, ad_metrics):
        for key, metric in bucket.items():
            previous_bucket = (
                previous_order if key in previous_order else
                previous_traffic if key in previous_traffic else
                previous_ads if key in previous_ads else {}
            )
            previous = previous_bucket.get(key)
            change = pct_change(metric.value, previous.value if previous else None)
            changes[key] = {
                "metric_id": key,
                "current": metric.value,
                "previous": previous.value if previous else None,
                "change": change,
                "formatted_change": "无可比数据" if change is None else f"{change * 100:.2f}%",
            }

    product_orders = product_order_metrics(orders, current)
    product_traffic = product_traffic_metrics(traffic, current)
    campaign = campaign_metrics(advertising, current)

    if not product_orders.empty and not product_traffic.empty:
        product_view = product_traffic.merge(
            product_orders[["product_id", "paid_gmv", "refund_amount", "refund_rate"]],
            on="product_id",
            how="left",
            suffixes=("", "_order"),
        )
    else:
        product_view = product_traffic if not product_traffic.empty else product_orders

    funnel = []
    if traffic_metrics:
        funnel = [
            {"stage": "曝光", "value": traffic_metrics.get("impressions").value if traffic_metrics.get("impressions") else 0},
            {"stage": "点击", "value": traffic_metrics.get("clicks").value if traffic_metrics.get("clicks") else 0},
            {"stage": "访客", "value": traffic_metrics.get("visitors").value if traffic_metrics.get("visitors") else 0},
            {"stage": "加购", "value": traffic_metrics.get("add_to_cart_users").value if traffic_metrics.get("add_to_cart_users") else 0},
            {"stage": "支付买家", "value": traffic_metrics.get("payment_buyers").value if traffic_metrics.get("payment_buyers") else 0},
        ]

    return {
        "current_period": current,
        "comparison_period": comparison if has_comparison else {},
        "has_comparison": has_comparison,
        "cards": _merge_cards(order_metrics, traffic_metrics, ad_metrics),
        "metrics": {
            "orders": _dict_metrics(order_metrics),
            "traffic": _dict_metrics(traffic_metrics),
            "advertising": _dict_metrics(ad_metrics),
        },
        "previous_metrics": {
            "orders": _dict_metrics(previous_order),
            "traffic": _dict_metrics(previous_traffic),
            "advertising": _dict_metrics(previous_ads),
        },
        "changes": changes,
        "charts": {
            "sales_trend": _records(daily_order_series(orders), 200),
            "funnel": funnel,
            "product_gmv_rank": _records(product_orders.sort_values("paid_gmv", ascending=False), 20),
            "high_traffic_low_conversion": _records(
                product_view.sort_values(["visitors", "payment_conversion_rate"], ascending=[False, True])
                if not product_view.empty and "visitors" in product_view.columns else product_view,
                20,
            ),
            "campaign_roas_rank": _records(_sort_if_present(campaign, "roas", ascending=True), 20),
            "refund_rank": _records(_sort_if_present(product_orders, "refund_amount", ascending=False), 20),
        },
        "tables": {
            "product_orders": _records(product_orders, 100),
            "product_traffic": _records(product_traffic, 100),
            "campaigns": _records(campaign, 100),
        },
        "format_examples": {
            "roas_formula": "广告投产比ROAS = ad_revenue / ad_spend",
            "currency_example": format_metric(1234.56, "currency"),
        },
    }
