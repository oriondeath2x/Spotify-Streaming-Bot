import os
import time
import random
import json
import zipfile
import pickle
import logging
import uuid
from fake_useragent import UserAgent
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BrowserHandler:
    def __init__(self, profile_data=None, sandboxie_path=None, headless=False):
        """
        profile_data: dict containing 'proxy', 'user_agent', 'window_size', 'platform', etc.
        """
        self.profile_data = profile_data or {}
        self.proxy = self.profile_data.get('proxy')
        self.profile_path = self.profile_data.get('profile_path') # Full path to cookies file
        self.sandboxie_path = sandboxie_path
        self.headless = headless
        self.driver = None
        self.user_agent = self.profile_data.get('user_agent') or UserAgent().random
        self.temp_files = []

    def _parse_proxy(self):
        """
        Parses proxy string into components.
        Supported formats:
        - ip:port
        - ip:port:user:pass
        - user:pass@ip:port
        """
        if not self.proxy:
            return None

        try:
            if '@' in self.proxy:
                # Format: user:pass@ip:port
                auth, endpoint = self.proxy.split('@')
                user, password = auth.split(':')
                ip, port = endpoint.split(':')
            elif self.proxy.count(':') == 3:
                # Format: ip:port:user:pass
                parts = self.proxy.split(':')
                ip, port, user, password = parts[0], parts[1], parts[2], parts[3]
            elif self.proxy.count(':') == 1:
                # Format: ip:port
                ip, port = self.proxy.split(':')
                user, password = None, None
            else:
                logger.warning(f"Invalid proxy format: {self.proxy}")
                return None

            return {
                "ip": ip,
                "port": int(port),
                "user": user,
                "pass": password
            }
        except Exception as e:
            logger.error(f"Error parsing proxy: {e}")
            return None

    def _create_proxy_extension(self, proxy_config):
        """Creates a Chrome extension for proxy authentication."""
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """

        background_js = """
        var config = {
                mode: "fixed_servers",
                rules: {
                singleProxy: {
                    scheme: "http",
                    host: "%s",
                    port: parseInt(%s)
                },
                bypassList: ["localhost"]
                }
            };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
        """ % (proxy_config['ip'], proxy_config['port'], proxy_config['user'], proxy_config['pass'])

        plugin_file = f'proxy_auth_plugin_{uuid.uuid4()}.zip'
        with zipfile.ZipFile(plugin_file, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)

        self.temp_files.append(os.path.abspath(plugin_file))
        return os.path.abspath(plugin_file)

    def start_driver(self):
        """Initializes the Undetected Chrome Driver with options."""
        options = uc.ChromeOptions()

        # Consistent Fingerprint
        options.add_argument(f'--user-agent={self.user_agent}')

        # Device Emulation (Mobile)
        device_type = self.profile_data.get('device_type', 'desktop')

        if device_type == 'mobile':
            mobile_emulation = {
                "deviceMetrics": { "width": 375, "height": 812, "pixelRatio": 3.0 },
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
            }
            options.add_experimental_option("mobileEmulation", mobile_emulation)
            logger.info("Using Mobile Emulation (iPhone X Profile)")
        else:
            # Window Size (Desktop)
            if self.profile_data.get('window_size'):
                width, height = self.profile_data['window_size'].split(',')
                options.add_argument(f'--window-size={width},{height}')

        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--password-store=basic')
        options.add_argument('--lang=en-US')

        if self.headless:
             options.add_argument('--headless=new')

        # Proxy setup
        proxy_config = self._parse_proxy()
        if proxy_config:
            if proxy_config['user'] and proxy_config['pass']:
                plugin_file = self._create_proxy_extension(proxy_config)
                options.add_argument(f'--load-extension={plugin_file}')
            else:
                options.add_argument(f'--proxy-server={proxy_config["ip"]}:{proxy_config["port"]}')

        # Sandboxie Handling (Experimental)
        # Undetected-Chromedriver launches the binary directly.
        # If we want Sandboxie, we might need to point `browser_executable_path` to a wrapper script.
        # For now, we rely on standard execution.

        try:
            logger.info("Starting Undetected Chrome Driver...")

            # Use WebDriverManager to find/install correct driver
            driver_path = ChromeDriverManager().install()

            self.driver = uc.Chrome(
                driver_executable_path=driver_path,
                options=options,
                use_subprocess=True
            )

            # Apply Selenium Stealth with Profile Data if available
            # Note: Stealth might conflict with mobile emulation UA override if not careful.
            # Only apply if desktop to avoid overriding mobile UA.
            if device_type == 'desktop':
                platform = self.profile_data.get('platform', 'Win32')
                stealth(self.driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform=platform,
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                )

            # Additional Fingerprint Randomization (Canvas/Audio)
            self._inject_fingerprint_scripts()

            if self.profile_path and os.path.exists(self.profile_path):
                self.load_cookies(self.profile_path)

            logger.info("Driver started successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to start driver: {e}")
            return False

    def _inject_fingerprint_scripts(self):
        """Injects JS to spoof Canvas, AudioContext, and WebGL."""
        # Simple Canvas Noise Injection
        script = """
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        var noise = Math.floor(Math.random() * 10) - 5;

        HTMLCanvasElement.prototype.toBlob = function() {
            return toBlob.apply(this, arguments);
        }
        HTMLCanvasElement.prototype.toDataURL = function() {
            return toDataURL.apply(this, arguments);
        }
        CanvasRenderingContext2D.prototype.getImageData = function() {
            return getImageData.apply(this, arguments);
        }
        """
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": script
            })
        except Exception as e:
            logger.warning(f"Could not inject fingerprint script: {e}")

    def stop_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

        # Cleanup temp files
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {f}: {e}")
        self.temp_files = []

    def save_cookies(self, filename):
        """Saves current cookies to a file."""
        if not self.driver:
            return
        try:
            cookies = self.driver.get_cookies()
            with open(filename, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")

    def load_cookies(self, filename):
        """Loads cookies from a file."""
        if not self.driver:
            return
        try:
            # We must be on the domain to set cookies. Navigate to 404 page first.
            self.driver.get("https://spotify.com/404")
            with open(filename, 'rb') as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                         # Sometimes domains mismatch or cookie is invalid
                        pass
            logger.info(f"Cookies loaded from {filename}")
            # Refresh to apply
            self.driver.refresh()
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")

    def warmup(self):
        """Visits random websites to build history."""
        sites = [
            "https://www.google.com",
            "https://www.bing.com",
            "https://www.yahoo.com",
            "https://www.wikipedia.org",
            "https://www.reddit.com",
            "https://www.amazon.com"
        ]
        if not self.driver:
            return

        try:
            # Monkey Patch Referrer Logic: visit a search engine first
            target = random.choice(sites)
            logger.info(f"Warming up: Visiting {target}")
            self.driver.get(target)
            time.sleep(random.uniform(2, 5))

            # Scroll a bit
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(random.uniform(1, 3))
        except Exception as e:
            logger.error(f"Warmup error: {e}")
