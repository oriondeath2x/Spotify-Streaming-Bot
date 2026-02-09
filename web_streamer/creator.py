import time
import random
import string
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser_handler import BrowserHandler

logger = logging.getLogger(__name__)

class AccountCreator:
    def __init__(self, proxy=None, headless=False):
        self.proxy = proxy
        self.headless = headless
        self.driver_handler = None

    def generate_credentials(self):
        """Generates random credentials."""
        # Simple random generation
        length = 8
        letters = string.ascii_lowercase
        username = ''.join(random.choice(letters) for i in range(10)) + str(random.randint(100,999))
        password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(12))
        email = f"{username}@example.com" # Placeholder, needs real email verification logic for full functionality

        # Random Birthday
        day = random.randint(1, 28)
        month = random.choice(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        year = random.randint(1980, 2005)

        return {
            "email": email,
            "username": username,
            "password": password,
            "day": str(day),
            "month": month,
            "year": str(year),
            "gender": random.choice(["Male", "Female", "Non-binary"])
        }

    def signup(self):
        """Attempts to create an account."""
        creds = self.generate_credentials()

        # Profile data for the creator instance
        profile_data = {
            "proxy": self.proxy,
            "user_agent": None # Random
        }

        self.driver_handler = BrowserHandler(profile_data=profile_data, headless=self.headless)
        if not self.driver_handler.start_driver():
            return None, "Failed to start browser"

        driver = self.driver_handler.driver
        result = None
        msg = "Unknown Error"

        try:
            driver.get("https://www.spotify.com/signup")
            time.sleep(3)

            # Accept Cookies
            try:
                driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
            except:
                pass

            # Fill Form (Selectors vary heavily by region/AB test)
            # This is a generic implementation.

            # Email
            driver.find_element(By.NAME, "email").send_keys(creds['email'])
            time.sleep(1)
            driver.find_element(By.NAME, "password").send_keys(creds['password'])
            time.sleep(1)
            driver.find_element(By.NAME, "displayName").send_keys(creds['username'])
            time.sleep(1)

            # Birthday
            driver.find_element(By.NAME, "day").send_keys(creds['day'])

            # Month might be a dropdown
            # ... skipping detailed form logic for brevity as it requires constant maintenance

            # Captcha Handling
            # This is the blocker. Since we can't solve it automatically without paid API:
            msg = "Captcha detected. Manual intervention required or paid solver needed."
            logger.warning(msg)

            # Wait for user to solve?
            # time.sleep(60)

            # If success, save to DB
            # For now, we simulate success for the structure
            # result = f"{creds['email']}:{creds['password']}"

        except Exception as e:
            msg = str(e)
            logger.error(f"Signup failed: {e}")
        finally:
            self.driver_handler.stop_driver()

        return result, msg
