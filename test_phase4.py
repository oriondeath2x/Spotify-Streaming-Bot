import unittest
import os
import sqlite3
from web_streamer.database import DatabaseManager
from web_streamer.scheduler import Scheduler

class TestPhase4(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_phase4.db"
        self.db = DatabaseManager(db_path=self.db_path)
        self.scheduler = Scheduler(self.db)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_shared_playlists(self):
        self.db.save_child_playlist("http://child1", "user1")
        self.db.save_child_playlist("http://child2", "user2")

        # Test getting random not from user1
        url = self.db.get_random_child_playlist(exclude_creator="user1")
        self.assertEqual(url, "http://child2")

        # Test getting any random
        url = self.db.get_random_child_playlist()
        self.assertIn(url, ["http://child1", "http://child2"])

    def test_scheduler_logic(self):
        task = self.scheduler.get_next_task("user1", "http://master")
        self.assertIn(task['action'], ["create_child_playlist", "stream_child", "stream_master"])

        # Test active accounts filter (default 00:00-23:59 should be active)
        self.db.add_account("user1", "pass", "proxy", "desktop")
        active = self.scheduler.get_active_accounts()
        self.assertEqual(len(active), 1)

if __name__ == '__main__':
    unittest.main()
