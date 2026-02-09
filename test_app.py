import unittest
import json
import os
import shutil
from web_streamer.app import app
from web_streamer.manager import BotManager
from web_streamer.profile_manager import ProfileManager

class TestStreamerApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_status_endpoint(self):
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)

    def test_config_endpoint(self):
        # Test GET
        response = self.app.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("mode", data)

        # Test POST
        payload = {
            "mode": "GENERATE",
            "target_url": "test_url"
        }
        response = self.app.post('/api/config', json=payload)
        self.assertEqual(response.status_code, 200)

        # Verify persistence
        response = self.app.get('/api/config')
        data = json.loads(response.data)
        self.assertEqual(data['mode'], "GENERATE")

    def test_reset_profiles(self):
        response = self.app.post('/api/reset')
        self.assertEqual(response.status_code, 200)

class TestBotManager(unittest.TestCase):
    def test_parse_accounts(self):
        manager = BotManager()
        lines = [
            "user1:pass1",
            "user2:pass2|ip:port:u:p",
            "invalid_line",
            ""
        ]
        parsed = manager.parse_accounts(lines)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['account'], "user1:pass1")
        self.assertIsNone(parsed[0]['proxy'])
        self.assertEqual(parsed[1]['account'], "user2:pass2")
        self.assertEqual(parsed[1]['proxy'], "ip:port:u:p")

class TestProfileManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_profiles"
        self.pm = ProfileManager(profiles_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_create_profile(self):
        profile = self.pm.get_or_create_profile("testuser")
        self.assertEqual(profile['username'], "testuser")
        self.assertIn("user_agent", profile)
        self.assertIn("platform", profile)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "testuser.json")))

    def test_persistence(self):
        p1 = self.pm.get_or_create_profile("user_persist")
        ua1 = p1['user_agent']

        # Reload
        p2 = self.pm.get_or_create_profile("user_persist")
        self.assertEqual(p2['user_agent'], ua1)

if __name__ == '__main__':
    unittest.main()
