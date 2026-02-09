import time
import logging
from selenium.webdriver.common.by import By
from .browser_handler import BrowserHandler
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class BanChecker:
    def __init__(self, headless=True):
        self.headless = headless
        self.db = DatabaseManager()

    def check_account(self, username, password, proxy=None):
        """
        Quickly logs in to verify account status.
        Returns: True (Active), False (Banned/Invalid)
        """
        profile_data = {
            "proxy": proxy,
            "device_type": "desktop",
            "user_agent": None # Random
        }

        handler = BrowserHandler(profile_data=profile_data, headless=self.headless)
        if not handler.start_driver():
            return False, "Browser Failed"

        driver = handler.driver
        status = "Unknown"
        is_active = False

        try:
            driver.get("https://accounts.spotify.com/en/login")
            time.sleep(3)

            # Already logged in check
            if "accounts.spotify.com" not in driver.current_url:
                status = "Active"
                is_active = True
            else:
                # Login
                driver.find_element(By.ID, "login-username").send_keys(username)
                driver.find_element(By.ID, "login-password").send_keys(password)
                try:
                    driver.find_element(By.ID, "login-button").click()
                except:
                     driver.find_element(By.XPATH, "//button[span[text()='Log In']]").click()

                time.sleep(5)

                # Check for errors
                if "accounts.spotify.com" in driver.current_url:
                    try:
                        error_elem = driver.find_element(By.CSS_SELECTOR, "[data-testid='login-error-message']")
                        error_text = error_elem.text.lower()
                        if "incorrect" in error_text:
                            status = "Invalid Credentials"
                        elif "disabled" in error_text:
                            status = "Banned"
                        else:
                             status = f"Error: {error_text}"
                    except:
                        # Maybe captcha
                         status = "Captcha/Unknown"
                else:
                    status = "Active"
                    is_active = True

        except Exception as e:
            status = f"Exception: {str(e)}"
        finally:
            handler.stop_driver()

        # Update DB
        self.db.update_account_status(username, status)
        return is_active, status

    def check_all(self):
        """Checks all accounts in DB."""
        accounts = self.db.get_accounts()
        results = []
        for acc in accounts:
            is_active, status = self.check_account(acc['username'], acc['password'], acc['proxy'])
            results.append({"username": acc['username'], "status": status})
            time.sleep(2) # Avoid rate limits
        return results
