import time
import threading
import logging
from .bot import SpotifyBot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.accounts = []
        self.proxies = []
        self.active_bots = {} # {username: SpotifyBot}
        self.lock = threading.Lock()

    def load_accounts(self, filepath):
        """Loads accounts from a file (user:pass)."""
        try:
            with open(filepath, 'r') as f:
                self.accounts = [line.strip() for line in f if ':' in line]
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

        with self.lock:
            if username in self.active_bots:
                if self.active_bots[username].is_alive():
                    return False, "Bot already running."
                else:
                    # Remove dead thread reference
                    del self.active_bots[username]

            bot = SpotifyBot(account, proxy, config)
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

        for i, account in enumerate(self.accounts):
            username, password = account.split(':')

            # Assign proxy (round-robin if fewer proxies than accounts, or None)
            proxy = None
            if self.proxies:
                proxy = self.proxies[i % proxy_count]

            success, msg = self.start_bot(username, password, proxy, config)
            if success:
                started_count += 1

            # Small delay between starts to avoid CPU spike
            time.sleep(2)

        return True, f"Started {started_count} bots."

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
