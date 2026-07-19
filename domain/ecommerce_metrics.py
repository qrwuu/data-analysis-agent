from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from models.metric_result import MetricResult


VALID_ORDER_STATUSES = {
    "paid",
    "completed",
    "shipped",
    "已支付",
    "已发货",
    "已完成",
    "交易成功",
}


def safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator is None or float(denominator) == 0:
        return None
    return float(numerator) / float(denominator)


def format_metric(value: float | int | None, unit: str = "") -> str:
    if value is None:
        return "无法计算"
    if unit == "currency":
        return f"¥{float(value):,.2f}"
    if unit == "percent":
        return f"{float(value) * 100:.2f}%"
    if unit == "ratio":
        return f"{float(value):.2f}"
    if unit == "count":
        return f"{int(round(float(value))):,}"
    return f"{float(value):,.2f}"


def _time_range(df: pd.DataFrame) -> dict[str, str]:
    if "date" not in df.columns or df.empty:
        return {}
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return {}
    return {
        "start": dates.min().strftime("%Y-%m-%d"),
        "end": dates.max().strftime("%Y-%m-%d"),
    }


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").fillna(0)


def _metric(
    metric_id: str,
    name: str,
    value: float | int | None,
    formula: str,
    source: str,
    time_range: dict[str, str],
    raw_values: dict[str, Any],
    unit: str,
) -> MetricResult:
    return MetricResult(
        metric_id=metric_id,
        name=name,
        value=None if value is None else float(value),
        formatted=format_metric(value, unit),
        formula=formula,
        source=source,
        time_range=time_range,
        raw_values=raw_values,
        unit=unit,
    )


def filter_period(df: pd.DataFrame, period: dict[str, str] | None = None) -> pd.DataFrame:
    if df is None or df.empty or not period or "date" not in df.columns:
        return df.copy() if df is not None else pd.DataFrame()
    dates = pd.to_datetime(df["date"], errors="coerce")
    start = pd.to_datetime(period.get("start"), errors="coerce")
    end = pd.to_datetime(period.get("end"), errors="coerce")
    mask = pd.Series([True] * len(df), index=df.index)
    if not pd.isna(start):
        mask &= dates >= start
    if not pd.isna(end):
        mask &= dates <= end
    return df.loc[mask].copy()


def effective_orders(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    data = df.copy()
    if "order_id" in data.columns:
        data = data.drop_duplicates(subset=["order_id"], keep="last")
    if "order_status" not in data.columns:
        return data.iloc[0:0].copy()
    status = data["order_status"].astype(str).str.strip()
    return data.loc[status.isin(VALID_ORDER_STATUSES)].copy()


def compute_order_metrics(df: pd.DataFrame, period: dict[str, str] | None = None, *, source: str = "orders") -> dict[str, MetricResult]:
    data = filter_period(df, period)
    valid = effective_orders(data)
    paid_gmv = float(_numeric(valid, "payment_amount").sum())
    paid_orders = int(valid["order_id"].nunique()) if "order_id" in valid.columns else 0
    paid_buyers = int(valid["buyer_id"].nunique()) if "buyer_id" in valid.columns else 0
    units_sold = float(_numeric(valid, "quantity").sum())
    refund_amount = float(_numeric(valid, "refund_amount").sum())
    average_order_value = safe_divide(paid_gmv, paid_orders)
    net_sales = paid_gmv - refund_amount
    refund_rate = safe_divide(refund_amount, paid_gmv)
    tr = _time_range(data)

    return {
        "paid_gmv": _metric("paid_gmv", "支付GMV", paid_gmv, "有效支付订单 payment_amount 求和", source, tr, {"payment_amount": paid_gmv}, "currency"),
        "paid_orders": _metric("paid_orders", "支付订单数", paid_orders, "有效支付订单 order_id 去重计数", source, tr, {"order_id_distinct": paid_orders}, "count"),
        "paid_buyers": _metric("paid_buyers", "支付买家数", paid_buyers, "有效支付订单 buyer_id 去重计数", source, tr, {"buyer_id_distinct": paid_buyers}, "count"),
        "units_sold": _metric("units_sold", "销售件数", units_sold, "quantity 求和", source, tr, {"quantity": units_sold}, "count"),
        "average_order_value": _metric("average_order_value", "客单价", average_order_value, "支付GMV / 支付订单数", source, tr, {"paid_gmv": paid_gmv, "paid_orders": paid_orders}, "currency"),
        "refund_amount": _metric("refund_amount", "退款金额", refund_amount, "refund_amount 求和", source, tr, {"refund_amount": refund_amount}, "currency"),
        "net_sales": _metric("net_sales", "净销售额", net_sales, "支付GMV - 退款金额", source, tr, {"paid_gmv": paid_gmv, "refund_amount": refund_amount}, "currency"),
        "refund_rate": _metric("refund_rate", "金额退款率", refund_rate, "退款金额 / 支付GMV", source, tr, {"refund_amount": refund_amount, "paid_gmv": paid_gmv}, "percent"),
    }


def compute_traffic_metrics(df: pd.DataFrame, period: dict[str, str] | None = None, *, source: str = "traffic") -> dict[str, MetricResult]:
    data = filter_period(df, period)
    impressions = float(_numeric(data, "impressions").sum())
    clicks = float(_numeric(data, "clicks").sum())
    visitors = float(_numeric(data, "visitors").sum())
    add_to_cart_users = float(_numeric(data, "add_to_cart_users").sum())
    payment_buyers = float(_numeric(data, "payment_buyers").sum())
    tr = _time_range(data)
    return {
        "ctr": _metric("ctr", "点击率CTR", safe_divide(clicks, impressions), "clicks / impressions", source, tr, {"clicks": clicks, "impressions": impressions}, "percent"),
        "add_to_cart_rate": _metric("add_to_cart_rate", "加购率", safe_divide(add_to_cart_users, visitors), "add_to_cart_users / visitors", source, tr, {"add_to_cart_users": add_to_cart_users, "visitors": visitors}, "percent"),
        "payment_conversion_rate": _metric("payment_conversion_rate", "支付转化率", safe_divide(payment_buyers, visitors), "payment_buyers / visitors", source, tr, {"payment_buyers": payment_buyers, "visitors": visitors}, "percent"),
        "visitors": _metric("visitors", "访客数", visitors, "visitors 求和", source, tr, {"visitors": visitors}, "count"),
        "impressions": _metric("impressions", "曝光量", impressions, "impressions 求和", source, tr, {"impressions": impressions}, "count"),
        "clicks": _metric("clicks", "点击量", clicks, "clicks 求和", source, tr, {"clicks": clicks}, "count"),
        "add_to_cart_users": _metric("add_to_cart_users", "加购人数", add_to_cart_users, "add_to_cart_users 求和", source, tr, {"add_to_cart_users": add_to_cart_users}, "count"),
        "payment_buyers": _metric("payment_buyers", "支付买家数", payment_buyers, "payment_buyers 求和", source, tr, {"payment_buyers": payment_buyers}, "count"),
    }


def compute_ad_metrics(df: pd.DataFrame, period: dict[str, str] | None = None, *, source: str = "advertising") -> dict[str, MetricResult]:
    data = filter_period(df, period)
    impressions = float(_numeric(data, "impressions").sum())
    clicks = float(_numeric(data, "clicks").sum())
    ad_spend = float(_numeric(data, "ad_spend").sum())
    ad_orders = float(_numeric(data, "ad_orders").sum())
    ad_revenue = float(_numeric(data, "ad_revenue").sum())
    tr = _time_range(data)
    return {
        "ad_ctr": _metric("ad_ctr", "广告点击率", safe_divide(clicks, impressions), "clicks / impressions", source, tr, {"clicks": clicks, "impressions": impressions}, "percent"),
        "cpc": _metric("cpc", "平均点击成本CPC", safe_divide(ad_spend, clicks), "ad_spend / clicks", source, tr, {"ad_spend": ad_spend, "clicks": clicks}, "currency"),
        "ad_conversion_rate": _metric("ad_conversion_rate", "广告转化率", safe_divide(ad_orders, clicks), "ad_orders / clicks", source, tr, {"ad_orders": ad_orders, "clicks": clicks}, "percent"),
        "roas": _metric("roas", "广告投产比ROAS", safe_divide(ad_revenue, ad_spend), "ad_revenue / ad_spend", source, tr, {"ad_revenue": ad_revenue, "ad_spend": ad_spend}, "ratio"),
        "ad_net_return_rate": _metric("ad_net_return_rate", "广告净回报率", safe_divide(ad_revenue - ad_spend, ad_spend), "(ad_revenue - ad_spend) / ad_spend", source, tr, {"ad_revenue": ad_revenue, "ad_spend": ad_spend}, "percent"),
        "ad_spend": _metric("ad_spend", "广告消耗", ad_spend, "ad_spend 求和", source, tr, {"ad_spend": ad_spend}, "currency"),
        "ad_revenue": _metric("ad_revenue", "广告成交金额", ad_revenue, "ad_revenue 求和", source, tr, {"ad_revenue": ad_revenue}, "currency"),
    }


def daily_order_series(df: pd.DataFrame) -> pd.DataFrame:
    valid = effective_orders(df)
    if valid.empty or "date" not in valid.columns:
        return pd.DataFrame(columns=["date", "paid_gmv", "refund_amount", "net_sales"])
    out = valid.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["payment_amount"] = _numeric(out, "payment_amount")
    out["refund_amount"] = _numeric(out, "refund_amount")
    grouped = out.groupby("date", dropna=True).agg(
        paid_gmv=("payment_amount", "sum"),
        refund_amount=("refund_amount", "sum"),
    ).reset_index()
    grouped["net_sales"] = grouped["paid_gmv"] - grouped["refund_amount"]
    return grouped.sort_values("date")


def product_order_metrics(df: pd.DataFrame, period: dict[str, str] | None = None) -> pd.DataFrame:
    valid = effective_orders(filter_period(df, period))
    if valid.empty or "product_id" not in valid.columns:
        return pd.DataFrame()
    data = valid.copy()
    if "product_name" not in data.columns:
        data["product_name"] = data["product_id"].astype(str)
    data["payment_amount"] = _numeric(data, "payment_amount")
    data["refund_amount"] = _numeric(data, "refund_amount")
    data["quantity"] = _numeric(data, "quantity")
    grouped = data.groupby(["product_id", "product_name"], dropna=False).agg(
        paid_gmv=("payment_amount", "sum"),
        refund_amount=("refund_amount", "sum"),
        units_sold=("quantity", "sum"),
        paid_orders=("order_id", "nunique") if "order_id" in data.columns else ("payment_amount", "count"),
    ).reset_index()
    grouped["refund_rate"] = grouped.apply(lambda row: safe_divide(row["refund_amount"], row["paid_gmv"]), axis=1)
    return grouped.sort_values("paid_gmv", ascending=False)


def product_traffic_metrics(df: pd.DataFrame, period: dict[str, str] | None = None) -> pd.DataFrame:
    data = filter_period(df, period)
    if data.empty or "product_id" not in data.columns:
        return pd.DataFrame()
    work = data.copy()
    if "product_name" not in work.columns:
        work["product_name"] = work["product_id"].astype(str)
    for col in ("impressions", "clicks", "visitors", "add_to_cart_users", "payment_buyers"):
        work[col] = _numeric(work, col)
    grouped = work.groupby(["product_id", "product_name"], dropna=False).agg(
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        visitors=("visitors", "sum"),
        add_to_cart_users=("add_to_cart_users", "sum"),
        payment_buyers=("payment_buyers", "sum"),
    ).reset_index()
    grouped["ctr"] = grouped.apply(lambda row: safe_divide(row["clicks"], row["impressions"]), axis=1)
    grouped["payment_conversion_rate"] = grouped.apply(lambda row: safe_divide(row["payment_buyers"], row["visitors"]), axis=1)
    return grouped.sort_values("visitors", ascending=False)


def campaign_metrics(df: pd.DataFrame, period: dict[str, str] | None = None) -> pd.DataFrame:
    data = filter_period(df, period)
    if data.empty or "campaign_id" not in data.columns:
        return pd.DataFrame()
    work = data.copy()
    for col in ("impressions", "clicks", "ad_spend", "ad_orders", "ad_revenue"):
        work[col] = _numeric(work, col)
    grouped = work.groupby(["campaign_id", "campaign_name", "product_id"], dropna=False).agg(
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        ad_spend=("ad_spend", "sum"),
        ad_orders=("ad_orders", "sum"),
        ad_revenue=("ad_revenue", "sum"),
    ).reset_index()
    grouped["roas"] = grouped.apply(lambda row: safe_divide(row["ad_revenue"], row["ad_spend"]), axis=1)
    grouped["ad_ctr"] = grouped.apply(lambda row: safe_divide(row["clicks"], row["impressions"]), axis=1)
    return grouped.sort_values("roas", ascending=True, na_position="last")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
