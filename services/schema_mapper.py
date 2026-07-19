from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from models.ecommerce_project import FieldMapping


ROLE_FIELDS: dict[str, list[str]] = {
    "orders": [
        "date",
        "order_id",
        "product_id",
        "sku_id",
        "product_name",
        "buyer_id",
        "quantity",
        "payment_amount",
        "refund_amount",
        "order_status",
    ],
    "traffic": [
        "date",
        "product_id",
        "product_name",
        "impressions",
        "clicks",
        "visitors",
        "add_to_cart_users",
        "payment_buyers",
    ],
    "advertising": [
        "date",
        "campaign_id",
        "campaign_name",
        "product_id",
        "impressions",
        "clicks",
        "ad_spend",
        "ad_orders",
        "ad_revenue",
    ],
}

REQUIRED_FIELDS: dict[str, set[str]] = {
    "orders": {"date", "order_id", "product_id", "buyer_id", "quantity", "payment_amount", "order_status"},
    "traffic": {"date", "product_id", "visitors", "payment_buyers"},
    "advertising": {"date", "campaign_id", "product_id", "ad_spend", "ad_revenue"},
}

ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "orders": {
        "date": ("日期", "下单日期", "支付日期", "date", "order_date", "pay_date"),
        "order_id": ("订单编号", "订单号", "order_id", "订单id", "交易编号"),
        "product_id": ("商品ID", "商品编号", "product_id", "商品id", "宝贝ID"),
        "sku_id": ("SKU_ID", "规格ID", "sku_id", "sku", "规格编码"),
        "product_name": ("商品名称", "product_name", "宝贝名称", "商品标题"),
        "buyer_id": ("买家ID", "用户ID", "buyer_id", "user_id", "客户ID"),
        "quantity": ("购买数量", "quantity", "件数", "商品数量", "销售件数"),
        "payment_amount": ("支付金额", "实付金额", "payment_amount", "成交金额", "订单金额"),
        "refund_amount": ("退款金额", "refund_amount", "退款", "售后金额"),
        "order_status": ("订单状态", "order_status", "状态", "交易状态"),
    },
    "traffic": {
        "date": ("日期", "date", "统计日期"),
        "product_id": ("商品ID", "商品编号", "product_id", "商品id", "宝贝ID"),
        "product_name": ("商品名称", "product_name", "宝贝名称", "商品标题"),
        "impressions": ("曝光量", "展现量", "impressions", "展示量"),
        "clicks": ("点击量", "clicks", "点击次数"),
        "visitors": ("访客数", "visitors", "UV", "访客"),
        "add_to_cart_users": ("加购人数", "add_to_cart_users", "加购用户数"),
        "payment_buyers": ("支付买家数", "成交买家数", "payment_buyers", "购买人数"),
    },
    "advertising": {
        "date": ("日期", "date", "统计日期"),
        "campaign_id": ("计划ID", "campaign_id", "推广计划ID", "广告计划ID"),
        "campaign_name": ("推广计划", "计划名称", "campaign_name", "广告计划"),
        "product_id": ("商品ID", "商品编号", "product_id", "商品id", "宝贝ID"),
        "impressions": ("曝光量", "展现量", "impressions", "展示量"),
        "clicks": ("点击量", "clicks", "点击次数"),
        "ad_spend": ("推广消耗", "广告花费", "ad_spend", "消耗", "花费"),
        "ad_orders": ("成交订单数", "ad_orders", "推广成交订单数"),
        "ad_revenue": ("推广成交金额", "广告成交金额", "ad_revenue", "广告销售额"),
    },
}

DATE_FIELDS = {"date"}
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
ID_FIELDS = {"order_id", "product_id", "sku_id", "buyer_id", "campaign_id"}


def normalize_name(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-_()/（）:：]+", "", text)
    return text


def _sample_values(series: pd.Series, limit: int = 20) -> list[Any]:
    return [item for item in series.dropna().head(limit).tolist()]


def _type_score(field: str, series: pd.Series) -> float:
    values = _sample_values(series)
    if not values:
        return 0.0
    if field in DATE_FIELDS:
        parsed = pd.to_datetime(pd.Series(values), errors="coerce")
        return float(parsed.notna().mean()) * 0.18
    if field in NUMERIC_FIELDS:
        numeric = pd.to_numeric(pd.Series(values), errors="coerce")
        return float(numeric.notna().mean()) * 0.16
    if field in ID_FIELDS:
        as_text = pd.Series(values).astype(str)
        non_empty = as_text.str.strip().ne("").mean()
        uniqueness_hint = min(1.0, as_text.nunique(dropna=True) / max(1, len(as_text)))
        return float(non_empty * 0.08 + uniqueness_hint * 0.06)
    return 0.03


def _name_score(column: str, aliases: tuple[str, ...]) -> float:
    normalized_column = normalize_name(column)
    normalized_aliases = [normalize_name(alias) for alias in aliases]
    if normalized_column in normalized_aliases:
        return 0.82
    best = 0.0
    for alias in normalized_aliases:
        if not alias:
            continue
        if alias in normalized_column or normalized_column in alias:
            best = max(best, 0.66)
        best = max(best, SequenceMatcher(None, normalized_column, alias).ratio() * 0.62)
    return best


def infer_field_mapping(role: str, df: pd.DataFrame, *, confidence_threshold: float = 0.72) -> dict[str, FieldMapping]:
    """Infer standard ecommerce fields for a dataframe.

    Returns one mapping entry for every standard field in the role. Missing
    required fields are represented explicitly so the caller can block analysis.
    """
    role = str(role or "").strip()
    if role not in ROLE_FIELDS:
        raise ValueError(f"Unsupported dataset role: {role}")

    columns = [str(col) for col in df.columns]
    used_columns: set[str] = set()
    result: dict[str, FieldMapping] = {}

    for field in ROLE_FIELDS[role]:
        candidates: list[tuple[float, str]] = []
        for column in columns:
            if column in used_columns:
                continue
            score = _name_score(column, ALIASES[role].get(field, (field,)))
            try:
                score += _type_score(field, df[column])
            except Exception:
                pass
            candidates.append((min(score, 0.99), column))
        candidates.sort(reverse=True, key=lambda item: item[0])
        best_score, best_column = candidates[0] if candidates else (0.0, "")
        confirmed = best_score >= confidence_threshold
        if confirmed and best_column:
            used_columns.add(best_column)
        required = field in REQUIRED_FIELDS[role]
        usable = best_score >= 0.60
        result[field] = FieldMapping(
            standard_field=field,
            source_field=best_column if usable else "",
            confidence=round(float(best_score), 3),
            confirmed=confirmed,
            required=required,
            missing=required and (not best_column or not usable),
        )
    return result


def mapping_from_payload(role: str, payload: dict[str, Any], current: dict[str, FieldMapping] | None = None) -> dict[str, FieldMapping]:
    """Merge user-confirmed mapping payload into inferred mapping."""
    base = dict(current or {})
    role_fields = ROLE_FIELDS.get(role, [])
    raw_mapping = payload.get("mapping") if isinstance(payload, dict) else payload
    raw_mapping = raw_mapping or {}
    for field in role_fields:
        existing = base.get(field) or FieldMapping(
            standard_field=field,
            required=field in REQUIRED_FIELDS.get(role, set()),
        )
        value = raw_mapping.get(field)
        if isinstance(value, dict):
            source = str(value.get("source_field") or value.get("source") or "").strip()
        else:
            source = str(value or "").strip()
        existing.source_field = source
        existing.confirmed = bool(source)
        existing.confidence = 1.0 if source else existing.confidence
        existing.missing = existing.required and not source
        base[field] = existing
    return base


def missing_required_fields(role: str, mapping: dict[str, FieldMapping]) -> list[str]:
    missing = []
    for field in sorted(REQUIRED_FIELDS.get(role, set())):
        item = mapping.get(field)
        if item is None or item.missing or not item.source_field:
            missing.append(field)
    return missing


def normalize_dataframe(role: str, df: pd.DataFrame, mapping: dict[str, FieldMapping]) -> pd.DataFrame:
    columns = {}
    for field, item in mapping.items():
        if item.source_field and item.source_field in df.columns:
            columns[item.source_field] = field
    normalized = df.rename(columns=columns).copy()
    keep = [field for field in ROLE_FIELDS.get(role, []) if field in normalized.columns]
    return normalized[keep].copy()
