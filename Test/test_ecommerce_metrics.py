import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.ecommerce_metrics import (
    compute_ad_metrics,
    compute_order_metrics,
    compute_traffic_metrics,
    effective_orders,
    safe_divide,
)


class EcommerceMetricTests(unittest.TestCase):
    def test_order_metrics_and_duplicate_dedup(self):
        df = pd.DataFrame([
            {"date": "2026-06-01", "order_id": "A1", "buyer_id": "B1", "product_id": "P1", "quantity": 1, "payment_amount": 100, "refund_amount": 10, "order_status": "交易成功"},
            {"date": "2026-06-01", "order_id": "A1", "buyer_id": "B1", "product_id": "P1", "quantity": 1, "payment_amount": 999, "refund_amount": 0, "order_status": "交易成功"},
            {"date": "2026-06-01", "order_id": "A2", "buyer_id": "B2", "product_id": "P2", "quantity": 2, "payment_amount": 200, "refund_amount": 20, "order_status": "已完成"},
            {"date": "2026-06-01", "order_id": "A3", "buyer_id": "B3", "product_id": "P2", "quantity": 1, "payment_amount": 300, "refund_amount": 0, "order_status": "已关闭"},
        ])
        valid = effective_orders(df)
        self.assertEqual(len(valid), 2)
        metrics = compute_order_metrics(df)
        self.assertEqual(metrics["paid_gmv"].value, 1199)
        self.assertEqual(metrics["net_sales"].value, 1179)
        self.assertEqual(metrics["paid_orders"].value, 2)
        self.assertEqual(metrics["average_order_value"].value, 599.5)
        self.assertAlmostEqual(metrics["refund_rate"].value, 20 / 1199)

    def test_traffic_and_ad_metrics(self):
        traffic = pd.DataFrame([{"date": "2026-06-01", "impressions": 1000, "clicks": 100, "visitors": 80, "add_to_cart_users": 20, "payment_buyers": 8}])
        tm = compute_traffic_metrics(traffic)
        self.assertEqual(tm["ctr"].value, 0.1)
        self.assertEqual(tm["payment_conversion_rate"].value, 0.1)

        ads = pd.DataFrame([{"date": "2026-06-01", "impressions": 1000, "clicks": 50, "ad_spend": 100, "ad_orders": 5, "ad_revenue": 450}])
        am = compute_ad_metrics(ads)
        self.assertEqual(am["roas"].value, 4.5)
        self.assertEqual(am["cpc"].value, 2)
        self.assertEqual(am["ad_net_return_rate"].value, 3.5)

    def test_zero_denominator(self):
        self.assertIsNone(safe_divide(10, 0))
        ads = pd.DataFrame([{"date": "2026-06-01", "impressions": 0, "clicks": 0, "ad_spend": 0, "ad_orders": 0, "ad_revenue": 0}])
        self.assertIsNone(compute_ad_metrics(ads)["roas"].value)


if __name__ == "__main__":
    unittest.main()

