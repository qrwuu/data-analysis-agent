import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import create_app


@unittest.skipIf(sys.version_info < (3, 10), "Flask application requires Python 3.10+")
class EcommerceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = create_app().test_client()

    def test_home_and_app_render(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        home = self.client.get("/ecommerce")
        self.assertEqual(home.status_code, 200)
        self.assertIn("数探 Agent", home.get_data(as_text=True))
        app = self.client.get("/ecommerce/app")
        self.assertEqual(app.status_code, 200)
        self.assertIn("数探 Agent", app.get_data(as_text=True))
        alias = self.client.get("/app")
        self.assertEqual(alias.status_code, 302)
        self.assertEqual(alias.headers.get("Location"), "/ecommerce/app")

    def test_demo_project_diagnosis_report(self):
        demo = self.client.post("/api/ecommerce/projects/demo")
        self.assertEqual(demo.status_code, 200)
        project = demo.get_json()
        self.assertGreaterEqual(len(project.get("diagnoses") or []), 3)

        ask = self.client.post(
            f"/api/ecommerce/projects/{project['project_id']}/ask",
            json={"question": "哪个推广计划最需要减少预算？"},
        )
        self.assertEqual(ask.status_code, 200)
        self.assertIn("tables_used", ask.get_json())

        report = self.client.post(f"/api/ecommerce/projects/{project['project_id']}/reports")
        self.assertEqual(report.status_code, 200)
        report_id = report.get_json()["report_id"]
        download = self.client.get(f"/api/ecommerce/projects/{project['project_id']}/reports/{report_id}/download")
        self.assertEqual(download.status_code, 200)

    def test_template_download_and_bad_role(self):
        self.assertEqual(self.client.get("/api/ecommerce/templates/orders").status_code, 200)
        self.assertEqual(self.client.get("/api/ecommerce/templates/bad").status_code, 404)


if __name__ == "__main__":
    unittest.main()
