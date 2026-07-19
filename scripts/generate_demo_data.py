#!/usr/bin/env python3
"""Generate deterministic ecommerce templates and demo workbooks.

The demo data intentionally contains:
- stable traffic but declining conversion for one product
- ad spend growth with ROAS decline
- elevated refund rate
- high traffic / low conversion product
- duplicated orders for data-quality checks
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "data_templates"
DEMO_DIR = ROOT / "demo_data"
SEED = 20260708

ORDER_FIELDS = [
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
]
TRAFFIC_FIELDS = [
    "date",
    "product_id",
    "product_name",
    "impressions",
    "clicks",
    "visitors",
    "add_to_cart_users",
    "payment_buyers",
]
AD_FIELDS = [
    "date",
    "campaign_id",
    "campaign_name",
    "product_id",
    "impressions",
    "clicks",
    "ad_spend",
    "ad_orders",
    "ad_revenue",
]

PRODUCTS = {
    "P001": ("轻奢通勤包", 199),
    "P002": ("夏季防晒衣", 89),
    "P003": ("智能保温杯", 129),
    "P004": ("儿童运动鞋", 159),
    "P005": ("家用收纳箱", 69),
}


def write_xlsx(path: Path, headers: list[str], rows: list[list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        width = max(12, min(28, max(len(str(cell.value or "")) for cell in col) + 2))
        ws.column_dimensions[col[0].column_letter].width = width
    wb.save(path)


def make_templates():
    write_xlsx(TEMPLATE_DIR / "orders_template.xlsx", ORDER_FIELDS, [])
    write_xlsx(TEMPLATE_DIR / "traffic_template.xlsx", TRAFFIC_FIELDS, [])
    write_xlsx(TEMPLATE_DIR / "advertising_template.xlsx", AD_FIELDS, [])


def daterange(start: date, days: int):
    for offset in range(days):
        yield start + timedelta(days=offset)


def make_traffic_rows():
    rows = []
    start = date(2026, 5, 25)
    for day in daterange(start, 14):
        current = day >= date(2026, 6, 1)
        for pid, (name, _price) in PRODUCTS.items():
            if pid == "P001":
                visitors = 105 if current else 104
                payment_buyers = 6 if current else 13
                impressions = 2600 if current else 2300
                clicks = 190 if current else 220
                carts = 22 if current else 21
            elif pid == "P002":
                visitors = 190 if current else 110
                payment_buyers = 3 if current else 7
                impressions = 3600 if current else 2100
                clicks = 210 if current else 160
                carts = 28 if current else 18
            elif pid == "P003":
                visitors = 72 if current else 70
                payment_buyers = 8 if current else 9
                impressions = 1500 if current else 1400
                clicks = 125 if current else 120
                carts = 14 if current else 15
            elif pid == "P004":
                visitors = 60 if current else 58
                payment_buyers = 7 if current else 7
                impressions = 1100 if current else 1060
                clicks = 100 if current else 96
                carts = 12 if current else 12
            else:
                visitors = 44 if current else 42
                payment_buyers = 5 if current else 5
                impressions = 900 if current else 860
                clicks = 80 if current else 76
                carts = 9 if current else 9
            rows.append([day.isoformat(), pid, name, impressions, clicks, visitors, carts, payment_buyers])
    return rows


def make_order_rows():
    random.seed(SEED)
    rows = []
    order_no = 10000
    start = date(2026, 5, 25)
    buyers_by_product = {
        "P001": (13, 6),
        "P002": (7, 3),
        "P003": (9, 8),
        "P004": (7, 7),
        "P005": (5, 5),
    }
    for day in daterange(start, 14):
        current = day >= date(2026, 6, 1)
        idx = 1 if current else 0
        for pid, (name, price) in PRODUCTS.items():
            buyers = buyers_by_product[pid][idx]
            for buyer_index in range(buyers):
                order_no += 1
                quantity = 1
                if pid == "P001" and not current and buyer_index % 5 == 0:
                    quantity = 2
                amount = price * quantity
                refund = 0
                if pid == "P003" and current and buyer_index in {0, 1, 2, 3, 4, 5}:
                    refund = amount
                status = "交易成功"
                rows.append([
                    day.isoformat(),
                    f"OD{order_no}",
                    pid,
                    f"{pid}-SKU1",
                    name,
                    f"B{pid[-1]}{buyer_index:03d}{day.day}",
                    quantity,
                    amount,
                    refund,
                    status,
                ])
    # A duplicate order with a slightly different amount to exercise quality checks.
    rows.append(list(rows[10]))
    rows[-1][7] = rows[-1][7] + 5
    return rows


def make_ad_rows():
    rows = []
    start = date(2026, 5, 25)
    campaigns = [
        ("C001", "通勤包搜索推广", "P001"),
        ("C002", "防晒衣信息流", "P002"),
        ("C003", "保温杯再营销", "P003"),
    ]
    for day in daterange(start, 14):
        current = day >= date(2026, 6, 1)
        for cid, name, pid in campaigns:
            if cid == "C001":
                spend = 155 if current else 100
                revenue = 430 if current else 620
                clicks = 90 if current else 85
                orders = 4 if current else 8
                impressions = 1600 if current else 1400
            elif cid == "C002":
                spend = 85 if current else 65
                revenue = 120 if current else 260
                clicks = 70 if current else 58
                orders = 2 if current else 4
                impressions = 1800 if current else 1200
            else:
                spend = 45 if current else 42
                revenue = 210 if current else 230
                clicks = 42 if current else 40
                orders = 3 if current else 3
                impressions = 760 if current else 730
            rows.append([day.isoformat(), cid, name, pid, impressions, clicks, spend, orders, revenue])
    return rows


def main():
    make_templates()
    write_xlsx(DEMO_DIR / "orders_demo.xlsx", ORDER_FIELDS, make_order_rows())
    write_xlsx(DEMO_DIR / "traffic_demo.xlsx", TRAFFIC_FIELDS, make_traffic_rows())
    write_xlsx(DEMO_DIR / "advertising_demo.xlsx", AD_FIELDS, make_ad_rows())
    print(f"Generated templates in {TEMPLATE_DIR}")
    print(f"Generated demo data in {DEMO_DIR}")


if __name__ == "__main__":
    main()
