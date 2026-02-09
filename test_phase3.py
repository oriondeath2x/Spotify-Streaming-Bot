import unittest
import json
import os
import shutil
import sqlite3
from web_streamer.app import app
from web_streamer.database import DatabaseManager
from web_streamer.profile_manager import ProfileManager

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_streamer.db"
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_account_ops(self):
        self.db.add_account("user1", "pass1", "proxy1", "desktop")
        accs = self.db.get_accounts()
        self.assertEqual(len(accs), 1)
        self.assertEqual(accs[0]['username'], "user1")

        self.db.update_account_status("user1", "Banned")
        accs = self.db.get_accounts(status="Banned")
        self.assertEqual(len(accs), 1)

    def test_stats_ops(self):
        self.db.increment_stat("streams_count")
        stats = self.db.get_stats()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]['streams'], 1)

class TestStreamerAppV3(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Monkey patch DB
        app.db = DatabaseManager(db_path="test_app_v3.db")

    def tearDown(self):
        if os.path.exists("test_app_v3.db"):
            os.remove("test_app_v3.db")

    def test_api_endpoints(self):
        # Stats
        res = self.app.get('/api/stats')
        self.assertEqual(res.status_code, 200)

        # Accounts
        res = self.app.get('/api/accounts')
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
