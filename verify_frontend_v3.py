from playwright.sync_api import sync_playwright
import time
import threading
from web_streamer.app import app

def run_server():
    app.run(port=5000, use_reloader=False)

def test_frontend_v3():
    # Start server in background
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://127.0.0.1:5000")

        # Check Tabs
        assert page.is_visible("#dashboard-tab")
        assert page.is_visible("#accounts-tab")
        assert page.is_visible("#creator-tab")

        # Check Stats Chart Canvas
        page.click("#accounts-tab")
        page.wait_for_selector("#statsChart")
        assert page.is_visible("#statsChart")

        # Check Creator Form
        page.click("#creator-tab")
        assert page.is_visible("#creatorForm")

        # Take screenshot
        page.screenshot(path="dashboard_v3_screenshot.png")
        browser.close()

if __name__ == "__main__":
    test_frontend_v3()
