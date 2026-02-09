import unittest
import json
from web_streamer.app import app

class TestStreamerApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_status_endpoint(self):
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_config_endpoint(self):
        payload = {
            "target_url": "https://open.spotify.com/track/123",
            "duration": 30,
            "warmup_enabled": False
        }
        response = self.app.post('/api/config', json=payload)
        self.assertEqual(response.status_code, 200)

        # Verify config update via subsequent get (or verify directly if exposed, currently only implicit via start)
        # We can check global CONFIG in app.py but cleaner to rely on api behavior.
        # However, api/status doesn't return config.
        # api/start uses config.

if __name__ == '__main__':
    unittest.main()
