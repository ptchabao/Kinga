import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app


class OnPremApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_and_health(self):
        root = self.client.get('/')
        self.assertEqual(root.status_code, 200)
        self.assertIn('message', root.json())

        health = self.client.get('/health')
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()['status'], 'ok')

    def test_onprem_status_endpoint(self):
        response = self.client.get('/api/onprem/status')
        self.assertEqual(response.status_code, 200)
        self.assertIn('deployment_mode', response.json())


if __name__ == '__main__':
    unittest.main()
