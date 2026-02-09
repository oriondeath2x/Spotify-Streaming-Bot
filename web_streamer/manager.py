import time
import threading
import logging
from .bot import SpotifyBot
from .profile_manager import ProfileManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.accounts = []
        self.proxies = []
        self.active_bots = {} # {username: SpotifyBot}
        self.lock = threading.Lock()
        self.profile_manager = ProfileManager()

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
        """Loads accounts from a file."""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            self.accounts = self.parse_accounts(lines)
            logger.info(f"Loaded {len(self.accounts)} accounts.")
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
        profile_data['profile_path'] = self.profile_manager.get_profile_path(username).replace('.json', '.pkl')

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

    def start_all(self, config):
        """Starts bots for all loaded accounts using available proxies."""
        if not self.accounts:
            return False, "No accounts loaded."

        started_count = 0
        proxy_count = len(self.proxies) if self.proxies else 0

        for i, entry in enumerate(self.accounts):
            # Entry is now a dict {"account": "u:p", "proxy": "..."}
            account = entry['account']
            specific_proxy = entry['proxy']

            username, password = account.split(':')

            # Determine Proxy Strategy
            # 1. Use specific proxy from account line (Combined format)
            # 2. Use mapped proxy from proxy list (1:1 mapping)
            # 3. Round robin (fallback)

            final_proxy = None

            if specific_proxy:
                final_proxy = specific_proxy
            elif self.proxies:
                # 1:1 Mapping attempt
                if i < proxy_count:
                     final_proxy = self.proxies[i]
                else:
                     # Round robin fallback
                     final_proxy = self.proxies[i % proxy_count]

            success, msg = self.start_bot(username, password, final_proxy, config)
            if success:
                started_count += 1

            # Small delay between starts to avoid CPU spike
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
