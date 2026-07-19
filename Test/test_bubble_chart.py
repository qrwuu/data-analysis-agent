import unittest

import pandas as pd

from Function.Charts_generation.charts.Bubble_Plot.chart import generate


class TestBubbleChartRendering(unittest.TestCase):
    def test_large_bubble_chart_uses_csp_safe_static_options(self):
        df = pd.DataFrame({
            "customer": [f"customer-{index}" for index in range(25)],
            "clicks": list(range(10, 260, 10)),
            "visitors": list(range(20, 270, 10)),
            "payment_buyers": list(range(1, 26)),
            "cluster": [index % 3 for index in range(25)],
        })
        result = generate(
            df,
            {"x": "clicks", "y": "visitors", "size": "payment_buyers", "color": "cluster"},
            {"title": "Cluster test"},
        )
        html = result.html
        self.assertNotIn("eval(", html)
        self.assertNotIn("function(p){return p.data", html)
        self.assertNotIn('"symbolSize": "function', html)
        self.assertIn('"symbolSize": 18', html)
        self.assertIn('"show": false', html)


if __name__ == "__main__":
    unittest.main()
