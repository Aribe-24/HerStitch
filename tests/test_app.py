import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


class HerStitchAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"HerStitch", response.data)

    def test_shop_page_loads(self):
        response = self.client.get("/shop")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Shop", response.data)

    def test_custom_order_form_submits(self):
        response = self.client.post(
            "/custom-orders",
            data={
                "name": "Test Client",
                "email": "test@example.com",
                "event_date": "2026-09-01",
                "details": "Need 10 stems for a bridal shower.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Thank you", response.data)


if __name__ == "__main__":
    unittest.main()
