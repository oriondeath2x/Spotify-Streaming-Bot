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
        Intelligently decides what the bot should do next (Swarm Logic).
        Strategies:
        1. Swarm Target: Check DB for specific targets (Artist, Album, Playlist).
        2. Collaborative: Create/Stream child playlists.
        3. Fallback: Stream Master.
        """
        rand = random.random()

        # 1. Swarm Target (Priority)
        swarm_target = self.db.get_swarm_target()
        if swarm_target:
            # If we found a specific target, use it 70% of the time
            if rand < 0.7:
                return {"action": "swarm_target", "url": swarm_target['url'], "type": swarm_target['type']}

        # 2. Child Playlists (Diversification)
        if rand < 0.2:
             return {"action": "create_child_playlist", "source": master_playlist_url}
        elif rand < 0.4:
             child_url = self.db.get_random_child_playlist(exclude_creator=username)
             if child_url:
                 return {"action": "stream_child", "url": child_url}

        # 3. Fallback
        return {"action": "stream_master", "url": master_playlist_url}

    def assign_song_from_master(self, master_url):
        """
        (Advanced) Parses master playlist and assigns the least-played song.
        Note: Requires scraping the playlist first to populate DB.
        For now, returns Master URL to let bot shuffle.
        """
        return master_url
