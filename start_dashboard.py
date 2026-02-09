import os
import sys
import webbrowser
import threading
import time

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    # Ensure dependencies are installed (optional check)

    print("Starting Spotify Streamer Dashboard...")
    threading.Thread(target=open_browser).start()

    # Run the Flask app as a module
    os.system(f"{sys.executable} -m web_streamer.app")
