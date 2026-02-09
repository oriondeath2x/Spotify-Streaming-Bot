from playwright.sync_api import sync_playwright
import time
import threading
from web_streamer.app import app

def run_server():
    app.run(port=5000, use_reloader=False)

def test_frontend_v4():
    # Start server in background
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://127.0.0.1:5000")

        # Check Updated Label
        label = page.locator("label:has-text('Target URL (Master Playlist/Song)')")
        assert label.is_visible()

        # Take screenshot
        page.screenshot(path="dashboard_v4_screenshot.png")
        browser.close()

if __name__ == "__main__":
    test_frontend_v4()
