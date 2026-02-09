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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpotifyBot(threading.Thread):
    def __init__(self, account, proxy, config):
        """
        account: "user:pass"
        proxy: "ip:port:user:pass" or similar
        config: dict with keys like 'target_url', 'duration', 'warmup_enabled', 'profile_path'
        """
        super().__init__()
        self.account = account
        self.username, self.password = account.split(':')
        self.proxy = proxy
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
            profile_path = self.config.get('profile_path', os.path.join("web_streamer", "profiles", f"{self.username}.pkl"))

            headless = self.config.get('headless', False)
            self.driver_handler = BrowserHandler(proxy=self.proxy, profile_path=profile_path, headless=headless)

            if not self.driver_handler.start_driver():
                self.log("Failed to start browser.")
                return

            driver = self.driver_handler.driver

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
            self.driver_handler.save_cookies(profile_path)

            # Stream
            self.log(f"Starting stream: {self.config.get('target_url')}")
            self._stream(driver)

        except Exception as e:
            self.log(f"Error: {str(e)}")
        finally:
            self.log("Session ended.")
            if self.driver_handler:
                self.driver_handler.stop_driver()
            self.is_running = False

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
            # Using multiple strategies to find the big green play button
            try:
                play_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='play-button']"))
                )
                play_button.click()
                self.log("Playback started.")
            except:
                 self.log("Could not find play button. Maybe already playing or different layout.")

            # Loop/Shuffle logic could be added here

            # Monitor
            while self.is_running and (time.time() - start_time < duration):
                remaining = int(duration - (time.time() - start_time))
                if remaining % 30 == 0: # Log every 30s
                    self.log(f"Streaming... {remaining}s remaining.")

                # Check if playing (optional: check progress bar or pause button existence)

                # Artificial Behavior: Randomly pause/resume or skip?
                # For now, just listen.

                time.sleep(5)

            self.log("Stream duration reached.")

        except Exception as e:
            self.log(f"Streaming error: {e}")
