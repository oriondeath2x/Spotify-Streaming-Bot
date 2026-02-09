import unittest
import os
import json
from web_streamer.actions import SpotifyActions
from web_streamer.database import DatabaseManager

class MockDriver:
    def __init__(self):
        pass

class TestPhase5(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_phase5.db"
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_selectors_loading(self):
        # Verify selectors.json exists and is valid
        self.assertTrue(os.path.exists("web_streamer/selectors.json"))
        with open("web_streamer/selectors.json", "r") as f:
            data = json.load(f)
        self.assertIn("login", data)
        self.assertIn("username_input", data["login"])

    def test_targets_db(self):
        self.db.add_target("http://target1", "artist", priority=10)
        self.db.add_target("http://target2", "playlist", priority=5)

        target = self.db.get_swarm_target()
        self.assertEqual(target['url'], "http://target1") # Priority 10 wins

if __name__ == '__main__':
    unittest.main()
