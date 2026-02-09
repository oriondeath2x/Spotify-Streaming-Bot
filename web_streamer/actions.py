import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class SpotifyActions:
    def __init__(self, driver):
        self.driver = driver

    def create_playlist(self, name, tracks=None):
        """Creates a playlist and adds tracks."""
        try:
            # Go to 'Create Playlist'
            # Note: Selectors change often. This is a best-effort.

            # Click "Create Playlist" in sidebar
            create_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='create-playlist-button']"))
            )
            create_btn.click()
            time.sleep(2)

            # Rename (Optional, defaults to "My Playlist #x")
            # Usually requires right-click or clicking the title.
            # Skipping specific rename to avoid complexity, Spotify auto-names.

            # Add Tracks via Search
            if tracks:
                # Find the search input within the playlist page
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[role='searchbox']"))
                )

                for track in tracks:
                    search_input.clear()
                    search_input.send_keys(track)
                    time.sleep(2)

                    # Click "Add" on first result
                    add_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='add-to-playlist-button']"))
                    )
                    add_btn.click()
                    time.sleep(1)

            # Get Playlist URL
            return self.driver.current_url

        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            return None

    def like_current_song(self):
        """Clicks the Heart/Like button for the currently playing song."""
        try:
            # Look for the heart button in the Now Playing bar
            like_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='add-button']"))
            )
            aria_label = like_btn.get_attribute("aria-label")
            if "Save" in aria_label or "Add" in aria_label:
                like_btn.click()
                logger.info("Liked current song.")
                return True
            else:
                logger.info("Song already liked.")
                return False
        except Exception as e:
            # Could be already liked (Remove button) or selector changed
            return False

    def follow_artist(self, artist_url):
        try:
            self.driver.get(artist_url)
            time.sleep(3)

            follow_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='user-widget-dropdown-follow-button']")) # Very likely to change
            )
            # Or look for text "Follow"
            if follow_btn.text.lower() == "follow":
                follow_btn.click()
                logger.info(f"Followed artist: {artist_url}")
                return True
        except:
            pass
        return False

    def search_and_play(self, query):
        """Searches for a song/artist and plays the first result."""
        try:
            search_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/search']"))
            )
            search_link.click()
            time.sleep(1)

            search_box = WebDriverWait(self.driver, 10).until(
                 EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='search-input']"))
            )
            search_box.clear()
            search_box.send_keys(query)
            time.sleep(3)

            # Click play on first result (Top Result)
            play_btn = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='play-button']")
            play_btn.click()
            return True
        except Exception as e:
            logger.error(f"Search and play failed: {e}")
            return False

    def skip_ad_if_possible(self):
        """Attempts to skip an ad if a button is present."""
        try:
            # Ad button text "Skip" or "Next"
            # Note: Spotify aggressively obfuscates this. This is best effort.
            # Look for button in ad container
            skip_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Skip') or contains(text(), 'Dismiss')]")
            skip_btn.click()
            logger.info("Skipped Ad.")
            return True
        except:
            return False

    def skip_track(self):
        """Clicks the 'Next' button."""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "button[data-testid='control-button-skip-forward']")
            next_btn.click()
            logger.info("Skipped Track.")
            return True
        except Exception as e:
            logger.error(f"Skip track failed: {e}")
            return False
