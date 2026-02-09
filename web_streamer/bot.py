import os
import time
import random
import logging
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser_handler import BrowserHandler
from .actions import SpotifyActions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpotifyBot(threading.Thread):
    def __init__(self, account, profile_data, config):
        """
        account: "user:pass"
        profile_data: dict containing proxy, ua, etc.
        config: dict with keys like 'target_url', 'duration', 'warmup_enabled'
        """
        super().__init__()
        self.account = account
        self.username, self.password = account.split(':')
        self.profile_data = profile_data
        self.proxy = profile_data.get('proxy')
        self.config = config
        self.driver_handler = None
        self.is_running = False
        self.status = "Stopped"
        self.log_messages = []

    def log(self, message):
        """Adds a log message."""
        timestamp = time.strftime("%H:%M:%S")
        msg = f"[{timestamp}] [{self.username}] {message}"
        self.log_messages.append(msg)
        # Keep log size manageable
        if len(self.log_messages) > 100:
            self.log_messages.pop(0)
        logger.info(msg)
        self.status = message # Update status for UI

    def stop(self):
        """Signals the bot to stop."""
        self.is_running = False
        self.log("Stopping...")

    def run(self):
        self.is_running = True
        self.log("Starting bot...")

        try:
            # profile_path is now in profile_data
            headless = self.config.get('headless', False)

            self.driver_handler = BrowserHandler(profile_data=self.profile_data, headless=headless)

            if not self.driver_handler.start_driver():
                self.log("Failed to start browser.")
                return

            driver = self.driver_handler.driver

            # Strict Proxy Check (Verify IP before login)
            # This requires Selenium to load an IP checker page.
            # self.log("Verifying Proxy...")
            # driver.get("https://api.ipify.org?format=json")
            # body_text = driver.find_element(By.TAG_NAME, "body").text
            # if self.proxy and self.proxy.split(':')[0] not in body_text:
            #     self.log(f"Proxy Mismatch! Expected {self.proxy} but got {body_text}")
            #     # return  <-- Strict mode would return here. Commented out for now to avoid false positives.

            # Warmup
            if self.config.get('warmup_enabled', True):
                self.log("Warming up...")
                self.driver_handler.warmup()

            # Login
            self.log("Attempting login...")
            if not self._login(driver):
                self.log("Login failed.")
                self.driver_handler.stop_driver()
                return

            # Save session for next time
            if 'profile_path' in self.profile_data:
                self.driver_handler.save_cookies(self.profile_data['profile_path'])

            # Determine Mode
            mode = self.config.get('mode', 'STREAM')
            self.log(f"Starting in {mode} mode.")

            actions = SpotifyActions(driver)

            # Auto-Scheduler Mode (Default)
            if mode == 'AUTO' or mode == 'STREAM':
                from .database import DatabaseManager
                from .scheduler import Scheduler
                db = DatabaseManager()
                scheduler = Scheduler(db)

                master = self.config.get('target_url')
                task = scheduler.get_next_task(self.username, master)
                action = task['action']

                self.log(f"Task Assigned: {action} -> {task.get('url', 'N/A')}")

                if action == "swarm_target":
                    # Handle specific types
                    self.config['target_url'] = task['url']
                    if task['type'] == 'artist':
                        actions.follow_artist(task['url'])
                        self._stream(driver) # Stream their popular songs
                    else:
                        self._stream(driver)

                elif action == "create_child_playlist":
                    # Create playlist logic
                    playlist_name = f"My Mix {random.randint(100,999)}"
                    artists = ["The Weeknd", "Taylor Swift", "Drake", "BTS", "Ed Sheeran"]
                    url = actions.create_playlist(playlist_name, tracks=random.sample(artists, 3))
                    if url:
                        self.log(f"Created Playlist: {url}")
                        db.save_child_playlist(url, self.username)

                elif action == "stream_child":
                    self.config['target_url'] = task['url']
                    self._stream(driver)

                else: # Fallback stream master
                    self.config['target_url'] = master
                    self._stream(driver)

            elif mode == 'ENGAGE':
                self.log("Starting Engagement (Like/Follow/Stream).")
                self._engage(driver, actions)

            # Record stream count
            self.increment_stat("streams_count")

        except Exception as e:
            self.log(f"Error: {str(e)}")
        finally:
            self.log("Session ended.")
            if self.driver_handler:
                self.driver_handler.stop_driver()
            self.is_running = False

    def increment_stat(self, stat_type):
        """Helper to increment stats in DB."""
        # Bot doesn't have direct DB access, but manager does.
        # Ideally, we should inject DB manager. For now, skipping to avoid circular dependency refactor.
        # Or, we can do a quick import inside method.
        try:
            from .database import DatabaseManager
            db = DatabaseManager()
            db.increment_stat(stat_type)
        except:
            pass

    def _login(self, driver):
        try:
            driver.get("https://accounts.spotify.com/en/login")

            # Check if already logged in (redirected)
            time.sleep(3)
            if "accounts.spotify.com" not in driver.current_url:
                self.log("Already logged in (Session resumed).")
                return True

            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "login-username"))
            )
            password_input = driver.find_element(By.ID, "login-password")

            username_input.clear()
            username_input.send_keys(self.username)
            password_input.clear()
            password_input.send_keys(self.password)

            # Handle Login Button (it varies by region/AB test)
            try:
                login_btn = driver.find_element(By.ID, "login-button")
                login_btn.click()
            except:
                # Fallback for "Log In" button text
                login_btn = driver.find_element(By.XPATH, "//button[span[text()='Log In']]")
                login_btn.click()

            time.sleep(5)

            # Check for errors
            if "accounts.spotify.com" in driver.current_url:
                # Still on login page? Check for error message
                try:
                    error = driver.find_element(By.CSS_SELECTOR, "[data-testid='login-error-message']") # Hypothetical selector
                    self.log(f"Login Error: {error.text}")
                    return False
                except:
                    # Maybe Captcha or 2FA
                    if "challenge" in driver.current_url:
                         self.log("Captcha/Challenge detected. Cannot proceed automatically.")
                         return False

            return True
        except Exception as e:
            self.log(f"Login exception: {e}")
            return False

    def _stream(self, driver):
        target_url = self.config.get('target_url')
        duration = int(self.config.get('duration', 60)) * 60 # Convert minutes to seconds
        start_time = time.time()

        try:
            driver.get(target_url)
            time.sleep(5)

            # Accept Cookies if popup exists
            try:
                cookie_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                cookie_btn.click()
            except:
                pass

            # Click Play
            try:
                # Use centralized selector via generic helper or specific action?
                # Since bot.py doesn't inherit SpotifyActions directly, we can instantiate it or move logic.
                # Better to use SpotifyActions if possible, but for raw click we can do:
                actions = SpotifyActions(driver)
                if actions._click_element("playback", "play_button"):
                    self.log("Playback started.")

                    # Engagement while streaming
                    if random.random() < 0.3: # 30% chance to like
                        actions.like_current_song()
                else:
                     self.log("Could not find play button. Maybe already playing.")
            except:
                 pass

            # Monitor with Smart Duration
            # Randomize total duration slightly (90-110%) to look organic
            real_duration = duration * random.uniform(0.9, 1.1)

            while self.is_running and (time.time() - start_time < real_duration):
                remaining = int(real_duration - (time.time() - start_time))

                # Check for Ads
                SpotifyActions(driver).skip_ad_if_possible()

                # Random Behavior: Skip Track (10% chance every min)
                if remaining % 60 == 0:
                     if random.random() < 0.1:
                         self.log("Simulating Skip.")
                         SpotifyActions(driver).skip_track()

                # Simulate Mouse Movements (Keep session alive)
                if random.random() < 0.05:
                    self.log("Humanizing: Moving Mouse.")
                    try:
                        # Simple JS mouse wiggle
                        driver.execute_script("""
                            var event = new MouseEvent('mousemove', {
                                'view': window,
                                'bubbles': true,
                                'cancelable': true,
                                'clientX': Math.random() * window.innerWidth,
                                'clientY': Math.random() * window.innerHeight
                            });
                            document.dispatchEvent(event);
                        """)
                    except:
                        pass

                if remaining % 30 == 0:
                    self.log(f"Streaming... {remaining}s remaining.")

                time.sleep(5)

            self.log("Stream duration reached.")

            # Post-Stream Wait (Session Continuity)
            wait_time = random.randint(60, 300)
            self.log(f"Waiting {wait_time}s before closing session...")
            time.sleep(wait_time)

        except Exception as e:
            self.log(f"Streaming error: {e}")

    def _engage(self, driver, actions):
        """Randomly browses, follows, likes, streams."""
        duration = int(self.config.get('duration', 60)) * 60
        start_time = time.time()

        while self.is_running and (time.time() - start_time < duration):
            # Pick random action
            action = random.choice(['search', 'home', 'library'])

            if action == 'search':
                query = random.choice(["lofi beats", "top hits", "rock classics", "jazz vibes"])
                self.log(f"Searching for {query}")
                actions.search_and_play(query)
                time.sleep(random.randint(30, 120)) # Listen for a bit

                if random.random() < 0.4:
                    actions.like_current_song()

            elif action == 'home':
                driver.get("https://open.spotify.com/")
                time.sleep(5)
                # Click a random playlist
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-click-handler']")
                    if cards:
                        random.choice(cards).click()
                        time.sleep(3)
                        # Play
                        driver.find_element(By.CSS_SELECTOR, "[data-testid='play-button']").click()
                        time.sleep(random.randint(30, 120))
                except:
                    pass

            time.sleep(5)
