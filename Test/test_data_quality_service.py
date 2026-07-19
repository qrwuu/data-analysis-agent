import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.data_quality_service import run_quality_checks


class DataQualityTests(unittest.TestCase):
    def test_quality_detects_duplicate_and_refund_issue(self):
        orders = pd.DataFrame([
            {"date": "2026-06-01", "order_id": "A1", "product_id": "P1", "buyer_id": "B1", "quantity": 1, "payment_amount": 100, "refund_amount": 0, "order_status": "交易成功"},
            {"date": "bad-date", "order_id": "A1", "product_id": "", "buyer_id": "B1", "quantity": 1, "payment_amount": 100, "refund_amount": 120, "order_status": "交易成功"},
        ])
        result = run_quality_checks({"orders": orders})
        types = {issue["issue_type"] for issue in result["issues"]}
        self.assertIn("duplicate_order_id", types)
        self.assertIn("invalid_date", types)
        self.assertIn("empty_product_id", types)
        self.assertTrue(result["blocking"])

    def test_product_coverage_warning(self):
        orders = pd.DataFrame([{"date": "2026-06-01", "order_id": "A1", "product_id": "P1", "buyer_id": "B1", "quantity": 1, "payment_amount": 100, "refund_amount": 0, "order_status": "交易成功"}])
        traffic = pd.DataFrame([{"date": "2026-06-01", "product_id": "P2", "visitors": 100, "payment_buyers": 10}])
        result = run_quality_checks({"orders": orders, "traffic": traffic})
        self.assertIn("traffic_order_product_coverage", {issue["issue_type"] for issue in result["issues"]})


if __name__ == "__main__":
    unittest.main()

