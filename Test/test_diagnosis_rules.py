import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.ecommerce_orchestrator import run_workflow
from services.schema_mapper import infer_field_mapping, normalize_dataframe


class DiagnosisRuleTests(unittest.TestCase):
    def test_demo_hits_expected_rules(self):
        root = Path(__file__).resolve().parent.parent
        roles = {
            "orders": root / "demo_data" / "orders_demo.xlsx",
            "traffic": root / "demo_data" / "traffic_demo.xlsx",
            "advertising": root / "demo_data" / "advertising_demo.xlsx",
        }
        datasets = {}
        for role, path in roles.items():
            df = pd.read_excel(path)
            mapping = infer_field_mapping(role, df)
            datasets[role] = normalize_dataframe(role, df, mapping)
        result = run_workflow(datasets)
        rules = {item["rule_id"] for item in result["diagnoses"]}
        self.assertGreaterEqual(len(rules), 3)
        self.assertIn("R3", rules)
        self.assertIn("R5", rules)
        self.assertIn("R4", rules)

    def test_no_false_positive_without_comparison(self):
        orders = pd.DataFrame([
            {"date": "2026-06-01", "order_id": "A1", "product_id": "P1", "buyer_id": "B1", "quantity": 1, "payment_amount": 100, "refund_amount": 0, "order_status": "交易成功"},
        ])
        traffic = pd.DataFrame([
            {"date": "2026-06-01", "product_id": "P1", "visitors": 10, "payment_buyers": 1, "impressions": 100, "clicks": 10, "add_to_cart_users": 2},
        ])
        result = run_workflow({"orders": orders, "traffic": traffic})
        self.assertNotIn("R3", {item["rule_id"] for item in result["diagnoses"]})


if __name__ == "__main__":
    unittest.main()

