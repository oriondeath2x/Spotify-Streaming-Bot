from flask import Flask, render_template, request, jsonify
import threading
import time
import os
from .manager import BotManager

app = Flask(__name__)
manager = BotManager()

# Global config storage
CONFIG = {
    "target_url": "",
    "duration": 60,
    "warmup_enabled": True,
    "threads": 1,
    "headless": False
}

@app.route('/')
def index():
    return render_template('index.html', config=CONFIG)

@app.route('/api/status')
def get_status():
    status = manager.get_status()
    return jsonify(status)

@app.route('/api/start', methods=['POST'])
def start_bot():
    data = request.json
    username = data.get('username')

    # Update config from request if provided
    CONFIG['target_url'] = data.get('target_url', CONFIG['target_url'])
    CONFIG['duration'] = int(data.get('duration', CONFIG['duration']))
    CONFIG['warmup_enabled'] = data.get('warmup_enabled', CONFIG['warmup_enabled'])
    CONFIG['headless'] = data.get('headless', CONFIG['headless'])

    if username == "all":
        manager.start_all(CONFIG)
        return jsonify({"message": "Started all bots."})
    else:
        # Start specific bot (not fully implemented in UI yet)
        return jsonify({"message": "Single bot start not implemented yet."})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    data = request.json
    username = data.get('username')

    if username == "all":
        manager.stop_all()
        return jsonify({"message": "Stopped all bots."})
    else:
        manager.stop_bot(username)
        return jsonify({"message": f"Stopped bot {username}."})

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json

    # Update accounts
    if 'accounts' in data:
        accounts = data['accounts'].split('\n')
        # Filter empty lines
        accounts = [a.strip() for a in accounts if a.strip()]
        manager.accounts = accounts # Direct assignment for simplicity, better to use load method
        # Also save to file for persistence
        with open('accounts.txt', 'w') as f:
            f.write('\n'.join(accounts))

    # Update proxies
    if 'proxies' in data:
        proxies = data['proxies'].split('\n')
        proxies = [p.strip() for p in proxies if p.strip()]
        manager.proxies = proxies
        with open('proxy.txt', 'w') as f:
            f.write('\n'.join(proxies))

    CONFIG['target_url'] = data.get('target_url', CONFIG['target_url'])
    CONFIG['duration'] = int(data.get('duration', CONFIG['duration']))
    CONFIG['warmup_enabled'] = data.get('warmup_enabled', CONFIG['warmup_enabled'])
    CONFIG['headless'] = data.get('headless', CONFIG['headless'])

    return jsonify({"message": "Config updated.", "accounts_count": len(manager.accounts), "proxies_count": len(manager.proxies)})

def run_app():
    # Load existing files if present
    if os.path.exists('accounts.txt'):
        manager.load_accounts('accounts.txt')
    if os.path.exists('proxy.txt'):
        manager.load_proxies('proxy.txt')

    # Security: Bind to localhost only and disable debug mode
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_app()
