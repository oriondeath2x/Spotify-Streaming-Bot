# Spotify Web Streamer (v2.0)

This is an advanced, undetectable web-based Spotify streaming bot.

## Features
- **Web Dashboard:** Manage bots, accounts, and proxies via a localhost interface.
- **Undetectable:** Uses `undetected-chromedriver` and `selenium-stealth` to evade detection.
- **Proxy Support:** Supports HTTP/SOCKS proxies with authentication (`ip:port:user:pass`).
- **Fingerprint Evasion:** Randomizes User-Agent, Canvas, WebGL, and AudioContext fingerprints.
- **Session Persistence:** Saves cookies to resume sessions without logging in again.
- **Warmup:** Browses random websites (Google, Bing, etc.) before streaming to build a realistic history.
- **Scheduler:** Stops bots after a set duration.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Edit `web_streamer/app.py` or `web_streamer/bot.py` for advanced configuration.

## Usage

1. Run the dashboard starter script:
   ```bash
   python start_dashboard.py
   ```
   This will launch the Flask server and open your default browser to `http://127.0.0.1:5000`.

2. **Configuration (Dashboard):**
   - **Target URL:** Enter the Spotify Playlist or Song URL.
   - **Duration:** Set how long each bot should run (in minutes).
   - **Warmup:** Enable to browse random sites before streaming.
   - **Headless Mode:** Check to run browsers in the background. Note: Headless mode is more detectable by Spotify.

3. **Data Input:**
   - **Accounts:** Paste your accounts in `user:pass` format (one per line).
   - **Proxies:** Paste your proxies in `ip:port:user:pass` or `user:pass@ip:port` format.
   - Click **Update Data** to load them.

4. **Control:**
   - Click **Start All** to launch bots for all loaded accounts.
   - Use the **Stop** buttons to stop individual bots or all at once.
   - Watch the **Status** table for real-time logs.

## Notes
- The bot runs in separate threads. Closing the dashboard window does not stop the bots (unless you stop the python process).
- Cookies are saved in `web_streamer/profiles/`.
- Logs are displayed in the dashboard and printed to the console.

## Disclaimer
This tool is for educational purposes only. Use responsibly.
