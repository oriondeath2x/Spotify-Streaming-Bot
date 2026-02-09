from playwright.sync_api import sync_playwright
import time
import threading
from web_streamer.app import app

def run_server():
    app.run(port=5000, use_reloader=False)

def test_frontend():
    # Start server in background
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://127.0.0.1:5000")

        # Check Mode Selector
        assert page.is_visible("#modeSelect")

        # Check Reset Button
        assert page.is_visible("#resetProfilesBtn")

        # Check if config loads (wait for default value or fetched value)
        page.wait_for_selector("#targetUrl")

        # Take screenshot
        page.screenshot(path="dashboard_screenshot.png")
        browser.close()

if __name__ == "__main__":
    test_frontend()
