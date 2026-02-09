import os
import json
import logging
import random
import time
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, profiles_dir="web_streamer/profiles"):
        self.profiles_dir = profiles_dir
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
        try:
            self.ua = UserAgent()
        except:
            self.ua = None # Fallback

    def get_profile_path(self, username):
        return os.path.join(self.profiles_dir, f"{username}.json")

    def load_profile(self, username):
        """Loads profile metadata if it exists."""
        path = self.get_profile_path(username)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load profile for {username}: {e}")
        return None

    def save_profile(self, username, data):
        """Saves profile metadata."""
        path = self.get_profile_path(username)
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Saved profile metadata for {username}")
        except Exception as e:
            logger.error(f"Failed to save profile for {username}: {e}")

    def get_or_create_profile(self, username, assigned_proxy=None):
        """
        Retrieves existing profile or creates a new one with a consistent fingerprint.
        If assigned_proxy is provided, it updates the profile with it.
        """
        profile = self.load_profile(username)

        if not profile:
            # Generate new consistent fingerprint
            platform_choice = random.choice(["Win32", "MacIntel", "Linux x86_64"])

            # Try to get a matching UA
            ua_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            if self.ua:
                try:
                    if "Win" in platform_choice:
                        ua_str = self.ua.chrome # simplify
                    elif "Mac" in platform_choice:
                        ua_str = self.ua.safari
                    else:
                        ua_str = self.ua.firefox
                except:
                    pass

            profile = {
                "username": username,
                "proxy": assigned_proxy,
                "user_agent": ua_str,
                "window_size": f"{random.randint(1024, 1920)},{random.randint(768, 1080)}",
                "platform": platform_choice,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_profile(username, profile)

        # If proxy changed/assigned externally, update it
        if assigned_proxy and profile.get("proxy") != assigned_proxy:
             profile["proxy"] = assigned_proxy
             self.save_profile(username, profile)

        return profile
