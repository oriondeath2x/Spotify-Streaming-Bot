import sqlite3
import logging
import json
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="web_streamer.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self.lock:
            conn = self._get_conn()
            c = conn.cursor()

            # Accounts Table
            # Stores authentication and basic device preference
            c.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        proxy TEXT,
                        status TEXT DEFAULT 'Active',
                        device_type TEXT DEFAULT 'desktop',
                        schedule TEXT DEFAULT '00:00-23:59',
                        last_used DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')

            # Profiles Table (Fingerprints)
            # Stores detailed browser fingerprint data for consistent identity
            c.execute('''CREATE TABLE IF NOT EXISTS profiles (
                        username TEXT PRIMARY KEY,
                        fingerprint_json TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')

            # Child Playlists Table
            c.execute('''CREATE TABLE IF NOT EXISTS shared_playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE,
                        creator_username TEXT,
                        source_master_url TEXT,
                        play_count INTEGER DEFAULT 0
                    )''')

            # Song Stats (Distribution)
            c.execute('''CREATE TABLE IF NOT EXISTS song_stats (
                        song_url TEXT PRIMARY KEY,
                        play_count INTEGER DEFAULT 0,
                        last_played_by TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')

            # Smart Targets Table (The Swarm Input)
            c.execute('''CREATE TABLE IF NOT EXISTS targets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE,
                        type TEXT, -- playlist, album, artist, track
                        priority INTEGER DEFAULT 5,
                        goal_plays INTEGER DEFAULT 1000,
                        current_plays INTEGER DEFAULT 0,
                        active BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')

            # Stats Table
            # Tracks daily metrics
            c.execute('''CREATE TABLE IF NOT EXISTS stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE UNIQUE,
                        streams_count INTEGER DEFAULT 0,
                        likes_count INTEGER DEFAULT 0,
                        follows_count INTEGER DEFAULT 0
                    )''')

            conn.commit()
            conn.close()

    def add_account(self, username, password, proxy=None, device_type='desktop'):
        """Adds a new account or ignores if duplicate."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO accounts (username, password, proxy, device_type) VALUES (?, ?, ?, ?)",
                          (username, password, proxy, device_type))
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            logger.error(f"DB Error add_account: {e}")
            return False

    def get_accounts(self, status=None):
        """Retrieves accounts, optionally filtered by status."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                if status:
                    c.execute("SELECT username, password, proxy, device_type FROM accounts WHERE status=?", (status,))
                else:
                    c.execute("SELECT username, password, proxy, device_type FROM accounts")
                rows = c.fetchall()
                conn.close()
            # Return list of dicts for easy access
            return [{"username": r[0], "password": r[1], "proxy": r[2], "device_type": r[3]} for r in rows]
        except Exception as e:
            logger.error(f"DB Error get_accounts: {e}")
            return []

    def update_account_status(self, username, status):
        """Updates the status (Active, Banned, etc.) of an account."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                c.execute("UPDATE accounts SET status=? WHERE username=?", (status, username))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"DB Error update_account_status: {e}")

    def save_profile(self, username, fingerprint_data):
        """Saves or updates browser fingerprint data."""
        try:
            conn = self._get_conn()
            c = conn.cursor()
            data_json = json.dumps(fingerprint_data)
            # Use REPLACE to update if exists
            c.execute("INSERT OR REPLACE INTO profiles (username, fingerprint_json) VALUES (?, ?)",
                      (username, data_json))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"DB Error save_profile: {e}")

    def get_profile(self, username):
        """Retrieves browser fingerprint data."""
        try:
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("SELECT fingerprint_json FROM profiles WHERE username=?", (username,))
            row = c.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            logger.error(f"DB Error get_profile: {e}")
            return None

    def increment_stat(self, stat_type="streams_count"):
        """Increments a daily statistic counter."""
        try:
            import datetime
            today = datetime.date.today().isoformat()

            # Map stat_type to column name securely
            valid_cols = ["streams_count", "likes_count", "follows_count"]
            col = stat_type if stat_type in valid_cols else "streams_count"

            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                # Ensure row exists for today
                c.execute("INSERT OR IGNORE INTO stats (date) VALUES (?)", (today,))
                # Increment
                c.execute(f"UPDATE stats SET {col} = {col} + 1 WHERE date=?", (today,))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"DB Error increment_stat: {e}")

    def get_stats(self):
        """Retrieves stats for the last 7 days."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                c.execute("SELECT date, streams_count, likes_count, follows_count FROM stats ORDER BY date DESC LIMIT 7")
                rows = c.fetchall()
                conn.close()
            return [{"date": r[0], "streams": r[1], "likes": r[2], "follows": r[3]} for r in rows]
        except Exception as e:
            logger.error(f"DB Error get_stats: {e}")
            return []

    def save_child_playlist(self, url, creator):
        """Saves a generated playlist."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO shared_playlists (url, creator_username) VALUES (?, ?)", (url, creator))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"DB Error save_child_playlist: {e}")

    def get_random_child_playlist(self, exclude_creator=None):
        """Returns a playlist URL not created by the requester."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                if exclude_creator:
                    c.execute("SELECT url FROM shared_playlists WHERE creator_username != ? ORDER BY RANDOM() LIMIT 1", (exclude_creator,))
                else:
                    c.execute("SELECT url FROM shared_playlists ORDER BY RANDOM() LIMIT 1")
                row = c.fetchone()
                conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"DB Error get_random_child_playlist: {e}")
            return None

    def add_target(self, url, target_type, priority=5):
        """Adds a target to the swarm."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO targets (url, type, priority) VALUES (?, ?, ?)",
                          (url, target_type, priority))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"DB Error add_target: {e}")

    def get_swarm_target(self):
        """Returns the highest priority target that hasn't met its goal."""
        try:
            with self.lock:
                conn = self._get_conn()
                c = conn.cursor()
                # Simple logic: High priority, then random
                c.execute("SELECT url, type FROM targets WHERE active=1 AND current_plays < goal_plays ORDER BY priority DESC, RANDOM() LIMIT 1")
                row = c.fetchone()
                conn.close()
            if row:
                return {"url": row[0], "type": row[1]}
            return None
        except Exception as e:
            logger.error(f"DB Error get_swarm_target: {e}")
            return None
