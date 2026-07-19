import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.schema_mapper import infer_field_mapping, missing_required_fields, normalize_dataframe


class SchemaMapperTests(unittest.TestCase):
    def test_chinese_alias_mapping(self):
        df = pd.DataFrame({
            "支付日期": ["2026-06-01"],
            "订单号": ["A1"],
            "商品ID": ["P1"],
            "用户ID": ["B1"],
            "购买数量": [1],
            "实付金额": [99],
            "退款金额": [0],
            "订单状态": ["交易成功"],
        })
        mapping = infer_field_mapping("orders", df)
        self.assertEqual(mapping["date"].source_field, "支付日期")
        self.assertEqual(mapping["payment_amount"].source_field, "实付金额")
        self.assertFalse(missing_required_fields("orders", mapping))
        normalized = normalize_dataframe("orders", df, mapping)
        self.assertIn("payment_amount", normalized.columns)

    def test_missing_required_fields(self):
        df = pd.DataFrame({"日期": ["2026-06-01"], "商品ID": ["P1"]})
        mapping = infer_field_mapping("orders", df)
        missing = missing_required_fields("orders", mapping)
        self.assertIn("order_id", missing)
        self.assertIn("payment_amount", missing)


if __name__ == "__main__":
    unittest.main()

