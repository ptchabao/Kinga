import unittest

from routers.onprem import build_onprem_dashboard, build_onprem_status


class OnPremTests(unittest.TestCase):
    def test_status_contains_deployment_mode(self):
        status = build_onprem_status()
        self.assertIn("deployment_mode", status)
        self.assertEqual(status["deployment_mode"], "dokploy-compose")

    def test_dashboard_contains_security_summary(self):
        dashboard = build_onprem_dashboard()
        self.assertIn("security", dashboard)
        self.assertIn("services", dashboard)
        self.assertIn("compliance", dashboard)


if __name__ == "__main__":
    unittest.main()
