import time
import random
import logging
import sqlite3
from datetime import datetime, time as dtime

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_active_accounts(self):
        """Returns accounts that should be running RIGHT NOW based on their schedule."""
        now = datetime.now().time()
        accounts = self.db.get_accounts(status="Active")
        active_now = []

        for acc in accounts:
            schedule = acc.get('schedule', '00:00-23:59')
            if not schedule: schedule = '00:00-23:59'

            try:
                start_str, end_str = schedule.split('-')
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()

                # Check if current time is within range
                if start_time <= end_time:
                    if start_time <= now <= end_time:
                        active_now.append(acc)
                else: # Crosses midnight (e.g. 22:00-02:00)
                    if now >= start_time or now <= end_time:
                         active_now.append(acc)
            except:
                # Default to active if parse error
                active_now.append(acc)

        return active_now

    def get_next_task(self, username, master_playlist_url):
        """
        Intelligently decides what the bot should do next.
        Strategies:
        1. Stream Master Playlist (if under-played).
        2. Create Child Playlist (if not enough child playlists exist).
        3. Stream a Child Playlist (to look organic).
        4. Stream Artist/Album directly.
        """
        # Simple probability logic for now
        rand = random.random()

        if rand < 0.1:
            return {"action": "create_child_playlist", "source": master_playlist_url}
        elif rand < 0.4:
            # Pick a child playlist created by someone else
            child_url = self.db.get_random_child_playlist(exclude_creator=username)
            if child_url:
                return {"action": "stream_child", "url": child_url}
            else:
                return {"action": "stream_master", "url": master_playlist_url}
        elif rand < 0.6:
            # Direct Artist/Album play (needs logic to extract from master, skipping for now)
            # Fallback to master
            return {"action": "stream_master", "url": master_playlist_url}
        else:
            return {"action": "stream_master", "url": master_playlist_url}

    def assign_song_from_master(self, master_url):
        """
        (Advanced) Parses master playlist and assigns the least-played song.
        Note: Requires scraping the playlist first to populate DB.
        For now, returns Master URL to let bot shuffle.
        """
        return master_url
