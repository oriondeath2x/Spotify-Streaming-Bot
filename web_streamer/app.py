from flask import Flask, render_template, request, jsonify
import threading
import time
import os
from .manager import BotManager
from .database import DatabaseManager
from .checker import BanChecker
from .creator import AccountCreator

app = Flask(__name__)
manager = BotManager()
db = DatabaseManager()

# Global config storage
CONFIG = {
    "target_url": "",
    "duration": 60,
    "warmup_enabled": True,
    "threads": 1,
    "headless": False,
    "mode": "STREAM",
    "shared_playlists": []
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
    CONFIG['mode'] = data.get('mode', CONFIG['mode'])

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

@app.route('/api/reset', methods=['POST'])
def reset_profiles():
    success, msg = manager.reset_profiles()
    return jsonify({"message": msg})

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = db.get_accounts()
    return jsonify(accounts)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = db.get_stats()
    return jsonify(stats)

@app.route('/api/check_bans', methods=['POST'])
def check_bans():
    checker = BanChecker(headless=CONFIG['headless'])
    results = checker.check_all()
    return jsonify({"message": "Check complete", "results": results})

@app.route('/api/create_account', methods=['POST'])
def create_account():
    data = request.json
    proxy = data.get('proxy')
    creator = AccountCreator(proxy=proxy, headless=False) # Headless False to see Captcha

    result, msg = creator.signup()

    if result:
        # Assuming result is "email:pass"
        try:
            user, pwd = result.split(':')
            db.add_account(user, pwd, proxy)
            return jsonify({"success": True, "message": f"Created: {user}"})
        except:
            return jsonify({"success": True, "message": f"Created but failed to parse: {result}"})
    else:
        return jsonify({"success": False, "message": msg})

@app.route('/api/config', methods=['GET', 'POST'])
def update_config():
    if request.method == 'GET':
        return jsonify({
            "target_url": CONFIG['target_url'],
            "duration": CONFIG['duration'],
            "warmup_enabled": CONFIG['warmup_enabled'],
            "headless": CONFIG['headless'],
            "mode": CONFIG['mode']
        })

    data = request.json

    # Update accounts
    if 'accounts' in data:
        lines = data['accounts'].split('\n')
        # Filter empty lines
        lines = [l.strip() for l in lines if l.strip()]
        manager.accounts = manager.parse_accounts(lines)
        # Also save to file for persistence (save the raw input)
        with open('accounts.txt', 'w') as f:
            f.write('\n'.join(lines))

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
    CONFIG['mode'] = data.get('mode', CONFIG['mode'])

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
