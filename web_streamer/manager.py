import time
import threading
import logging
from .bot import SpotifyBot
from .profile_manager import ProfileManager
from .database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.accounts = []
        self.proxies = []
        self.active_bots = {} # {username: SpotifyBot}
        self.lock = threading.Lock()
        self.db = DatabaseManager()
        self.profile_manager = ProfileManager(db_manager=self.db)

    def parse_accounts(self, text_lines):
        """Helper to parse a list of strings into account objects."""
        parsed = []
        for line in text_lines:
            line = line.strip()
            if not line: continue

            if '|' in line:
                acc_part, proxy_part = line.split('|', 1)
                if ':' in acc_part:
                    parsed.append({
                        "account": acc_part.strip(),
                        "proxy": proxy_part.strip()
                    })
            elif ':' in line:
                parsed.append({
                    "account": line,
                    "proxy": None
                })
        return parsed

    def load_accounts(self, filepath):
        """Loads accounts from a file and syncs to DB."""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()

            parsed = self.parse_accounts(lines)
            self.accounts = parsed

            # Sync to DB
            for entry in parsed:
                try:
                    user, pwd = entry['account'].split(':')
                    proxy = entry['proxy']
                    self.db.add_account(user, pwd, proxy)
                except:
                    pass

            logger.info(f"Loaded {len(self.accounts)} accounts and synced to DB.")
            return True, f"Loaded {len(self.accounts)} accounts."
        except Exception as e:
            return False, str(e)

    def load_proxies(self, filepath):
        """Loads proxies from a file (various formats)."""
        try:
            with open(filepath, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.proxies)} proxies.")
            return True, f"Loaded {len(self.proxies)} proxies."
        except Exception as e:
            return False, str(e)

    def start_bot(self, username, password, proxy, config):
        """Starts a single bot instance."""
        account = f"{username}:{password}"

        # Get or create persistent profile
        # If proxy is provided (from Load Proxies or UI), it will be assigned/updated in the profile.
        # If proxy is None, the profile manager will keep the existing one if present.
        profile_data = self.profile_manager.get_or_create_profile(username, assigned_proxy=proxy)

        # Ensure the profile path is correct for cookies
        profile_data['profile_path'] = self.profile_manager.get_cookies_path(username)

        with self.lock:
            if username in self.active_bots:
                if self.active_bots[username].is_alive():
                    return False, "Bot already running."
                else:
                    # Remove dead thread reference
                    del self.active_bots[username]

            # Pass profile_data instead of raw proxy
            # Pass a COPY of config to avoid shared state issues (except shared_playlists which should be shared)
            # However, shallow copy of dict means list references are preserved!
            # So shared_playlists will still point to the same list. Good.
            bot_config = config.copy()
            bot = SpotifyBot(account, profile_data, bot_config)
            bot.daemon = True # Allow main thread to exit
            bot.start()
            self.active_bots[username] = bot
            return True, "Bot started."

    def stop_bot(self, username):
        """Stops a specific bot."""
        with self.lock:
            if username in self.active_bots:
                bot = self.active_bots[username]
                bot.stop()
                # We don't delete immediately, let the thread finish.
                # But UI might want to remove it.
                return True, "Stop signal sent."
            return False, "Bot not found."

    def start_smart_rotation(self, config):
        """Manages rotating bots if account count > concurrency."""
        concurrency = int(config.get('concurrency', 5))
        duration = int(config.get('duration', 60))

        # This needs to run in a separate background thread
        def rotation_loop():
            logger.info("Starting Smart Rotation Loop")
            while True:
                # Get accounts sorted by last_used (Least Recently Used first)
                # Note: DB call needed here. Manager has DB instance.
                # Since get_accounts doesn't sort, we might need a new DB method or sort in memory.
                all_accounts = self.db.get_accounts()
                # Sort by last_used (None is treated as oldest/first)
                all_accounts.sort(key=lambda x: str(x.get('last_used') or ''))

                active_count = len(self.active_bots)
                slots_available = concurrency - active_count

                if slots_available > 0:
                    for acc in all_accounts:
                        if slots_available <= 0: break
                        if acc['username'] in self.active_bots: continue

                        # Check ban status
                        if acc.get('status') == 'Banned': continue

                        logger.info(f"Rotation: Starting {acc['username']}")
                        self.start_bot(acc['username'], acc['password'], acc['proxy'], config)
                        slots_available -= 1
                        time.sleep(5)

                time.sleep(10) # Check every 10s

        t = threading.Thread(target=rotation_loop, daemon=True)
        t.start()
        return True, "Smart Rotation started in background."

    def start_all(self, config):
        """Starts bots for all loaded accounts using available proxies."""
        if config.get('rotation'):
            return self.start_smart_rotation(config)

        if not self.accounts:
            # Fallback to DB accounts if memory is empty
            db_accs = self.db.get_accounts()
            if not db_accs:
                return False, "No accounts loaded."
            # Convert DB format to memory format for this method
            self.accounts = [{"account": f"{a['username']}:{a['password']}", "proxy": a['proxy']} for a in db_accs]

        # Concurrency limit for standard start
        limit = int(config.get('concurrency', 9999))

        started_count = 0
        proxy_count = len(self.proxies) if self.proxies else 0

        for i, entry in enumerate(self.accounts):
            if started_count >= limit: break

            # Entry is now a dict {"account": "u:p", "proxy": "..."}
            account = entry['account']
            specific_proxy = entry['proxy']

            username, password = account.split(':')

            # Determine Proxy Strategy
            final_proxy = specific_proxy
            if not final_proxy and self.proxies:
                final_proxy = self.proxies[i % proxy_count]

            success, msg = self.start_bot(username, password, final_proxy, config)
            if success:
                started_count += 1
                time.sleep(2)

        return True, f"Started {started_count} bots."

    def reset_profiles(self):
        """Deletes all profile metadata to force new fingerprints."""
        try:
            import shutil
            if os.path.exists(self.profile_manager.profiles_dir):
                shutil.rmtree(self.profile_manager.profiles_dir)
                os.makedirs(self.profile_manager.profiles_dir)
            return True, "Profiles reset."
        except Exception as e:
            return False, str(e)

    def stop_all(self):
        """Stops all running bots."""
        with self.lock:
            for username, bot in self.active_bots.items():
                bot.stop()
            return True, "Stop signal sent to all bots."

    def get_status(self):
        """Returns the status of all bots."""
        status_list = []
        with self.lock:
            # Clean up dead threads
            dead_bots = [u for u, b in self.active_bots.items() if not b.is_alive()]
            # For UI purposes, we might want to keep history, but for now just remove.
            # Actually, keep them but mark as stopped.

            for username, bot in self.active_bots.items():
                status_list.append({
                    "username": username,
                    "proxy": bot.proxy,
                    "status": "Running" if bot.is_alive() else "Stopped",
                    "logs": bot.log_messages[-5:] if hasattr(bot, 'log_messages') else [],
                    "last_log": bot.log_messages[-1] if bot.log_messages else ""
                })
        return status_list
