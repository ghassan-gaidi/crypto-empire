#!/usr/bin/env python3
"""
Crypto Empire - Web Dashboard & API
Autonomous crypto intelligence platform with monetization
"""
import os
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from html import unescape

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import requests

# ============================================================
# Configuration
# ============================================================
WALLET_ADDRESS = "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef"
if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp") / "crypto-empire-data"
else:
    DATA_DIR = Path.home() / "crypto-empire" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET", "crypto-empire-secret-key-2026")

# ============================================================
# Database
# ============================================================
DB_PATH = DATA_DIR / "web.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS price_cache (
            coin_id TEXT PRIMARY KEY,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# API helpers
# ============================================================
COINGECKO_API = "https://api.coingecko.com/api/v3"
CACHE_TTL = 60

def fetch_sync(url):
    try:
        resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def fetch_rss(url):
    """Fetch and parse an RSS feed"""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = []
            for item in root.iter('item'):
                title = item.findtext('title', '')
                link = item.findtext('link', '')
                pubDate = item.findtext('pubDate', '')
                desc = item.findtext('description', '')
                # Strip HTML from description
                desc_clean = re.sub(r'<[^>]+>', '', desc)[:200] if desc else ''
                items.append({
                    'title': unescape(title),
                    'link': link,
                    'date': pubDate,
                    'desc': unescape(desc_clean)
                })
            return items[:10]
    except:
        pass
    return []

# ============================================================
# HTML Template
# ============================================================
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Empire — Autonomous Crypto Intelligence</title>
    <style>
        :root {
            --bg: #0a0b0e;
            --card: #13151a;
            --border: #1e2030;
            --accent: #00d4aa;
            --accent2: #7c3aed;
            --text: #e2e8f0;
            --muted: #64748b;
            --danger: #ef4444;
            --success: #22c55e;
            --warning: #f59e0b;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        header {
            border-bottom: 1px solid var(--border);
            padding: 16px 0;
            margin-bottom: 30px;
        }
        header .container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }
        .logo { font-size: 24px; font-weight: bold; color: var(--accent); text-decoration: none; }
        .logo span { color: var(--accent2); }
        nav { display: flex; gap: 8px; flex-wrap: wrap; }
        nav a {
            color: var(--muted);
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.2s;
        }
        nav a:hover { color: var(--text); background: var(--card); }
        .btn {
            display: inline-block;
            background: var(--accent);
            color: #000;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            border: none;
            cursor: pointer;
            text-decoration: none;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.9; }
        .btn-purple { background: var(--accent2); }
        .btn-outline {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
        }
        .btn-sm { padding: 4px 12px; font-size: 12px; }
        
        h2.section-title {
            font-size: 16px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
            margin-top: 30px;
        }
        
        /* Top bar stats */
        .top-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            display: flex;
            flex-direction: column;
        }
        .stat-card .label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
        .stat-card .value { font-size: 22px; font-weight: 700; margin-top: 4px; }
        .stat-card .sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
        .up { color: var(--success); }
        .down { color: var(--danger); }
        
        /* Gas grid */
        .gas-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 24px; }
        .gas-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .gas-card .chain { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
        .gas-card .gwei { font-size: 20px; font-weight: 700; }
        .low { color: var(--success); }
        .medium { color: var(--warning); }
        .high { color: var(--danger); }
        
        /* Market table */
        .table-wrap {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow-x: auto;
            margin-bottom: 24px;
        }
        table { width: 100%; border-collapse: collapse; min-width: 600px; }
        th, td { padding: 10px 16px; text-align: left; font-size: 13px; white-space: nowrap; }
        th { color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        td { border-bottom: 1px solid rgba(30, 32, 48, 0.5); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(0, 212, 170, 0.03); }
        .rank { color: var(--muted); width: 30px; }
        .coin-name { font-weight: 600; }
        .coin-symbol { color: var(--muted); font-size: 11px; }
        .mc, .vol { color: var(--muted); font-size: 12px; }
        .sparkline { width: 100px; height: 30px; }
        
        /* Donation */
        .donation-box {
            background: linear-gradient(135deg, rgba(0,212,170,0.05), rgba(124,58,237,0.05));
            border: 1px solid var(--accent);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            text-align: center;
        }
        .donation-box h3 { color: var(--accent); font-size: 18px; margin-bottom: 8px; }
        .wallet-addr {
            background: var(--bg);
            padding: 10px 16px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            color: var(--accent);
            word-break: break-all;
            cursor: pointer;
            border: 1px solid var(--border);
            display: inline-block;
            max-width: 100%;
            user-select: all;
        }
        .wallet-addr:hover { border-color: var(--accent); }
        .chain-tags { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; margin: 10px 0; }
        .chain-tag {
            background: var(--bg);
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            color: var(--muted);
            border: 1px solid var(--border);
        }
        
        /* News */
        .news-list { list-style: none; }
        .news-list li {
            padding: 10px 0;
            border-bottom: 1px solid rgba(30, 32, 48, 0.5);
        }
        .news-list li:last-child { border-bottom: none; }
        .news-list a {
            color: var(--text);
            text-decoration: none;
            font-size: 14px;
            display: block;
        }
        .news-list a:hover { color: var(--accent); }
        .news-date { font-size: 11px; color: var(--muted); margin-top: 2px; }
        
        /* Features grid */
        .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }
        .feature-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }
        .feature-card:hover { border-color: var(--accent2); }
        .feature-icon { font-size: 28px; margin-bottom: 6px; }
        .feature-card h4 { font-size: 14px; margin-bottom: 4px; }
        .feature-card p { font-size: 12px; color: var(--muted); }
        
        /* Footer */
        footer { text-align: center; padding: 24px 0; border-top: 1px solid var(--border); color: var(--muted); font-size: 12px; }
        footer a { color: var(--accent); text-decoration: none; }
        
        .toast {
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            background: var(--accent); color: #000; padding: 10px 20px;
            border-radius: 8px; font-size: 13px; font-weight: 600;
            opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 100;
        }
        .toast.show { opacity: 1; }
        
        @media (max-width: 640px) {
            .container { padding: 12px; }
            .top-bar { grid-template-columns: repeat(2, 1fr); }
            th, td { padding: 8px 10px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">Crypto <span>Empire</span></a>
            <nav>
                <a href="#market">Market</a>
                <a href="#gas">Gas</a>
                <a href="#news">News</a>
                <a href="#features">Features</a>
                <a href="/docs">API</a>
                <a href="https://github.com/ghassan-gaidi/crypto-empire" target="_blank">GitHub</a>
                <a class="btn btn-sm" href="#donate">☕ Support</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <!-- Top coins bar -->
        <div class="top-bar">
            {% for coin_id, data in top_coins.items() %}
            <div class="stat-card">
                <div class="label">{{ coin_id|upper }}</div>
                <div class="value">${{ "%.2f"|format(data.usd) if data.usd < 1000 else "%.0f"|format(data.usd) }}</div>
                <div class="sub {{ 'up' if data.usd_24h_change >= 0 else 'down' }}">24h: {{ "%.2f"|format(data.usd_24h_change) }}%</div>
            </div>
            {% endfor %}
            {% if fear_greed %}
            <div class="stat-card">
                <div class="label">Fear & Greed</div>
                <div class="value" style="color: {{ 'var(--success)' if fear_greed.value > 50 else 'var(--danger)' if fear_greed.value < 25 else 'var(--warning)' }};">{{ fear_greed.value }}</div>
                <div class="sub">{{ fear_greed.classification }}</div>
            </div>
            {% endif %}
        </div>

        <!-- Gas Tracker -->
        <h2 class="section-title" id="gas">⛽ Gas Tracker</h2>
        <div class="gas-grid" id="gas-grid">
            <div class="gas-card"><div class="chain">Ethereum</div><div class="gwei" id="gas-eth">—</div></div>
            <div class="gas-card"><div class="chain">Polygon</div><div class="gwei" id="gas-poly">—</div></div>
            <div class="gas-card"><div class="chain">Arbitrum</div><div class="gwei" id="gas-arb">—</div></div>
            <div class="gas-card"><div class="chain">Base</div><div class="gwei" id="gas-base">—</div></div>
        </div>

        <!-- Market Table -->
        <h2 class="section-title" id="market">📊 Top 20 Cryptocurrencies</h2>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr><th>#</th><th>Name</th><th>Price</th><th>24h</th><th>7d</th><th>Market Cap</th><th>Volume (24h)</th></tr>
                </thead>
                <tbody>
                    {% for coin in market_data %}
                    <tr>
                        <td class="rank">{{ coin.market_cap_rank }}</td>
                        <td><span class="coin-name">{{ coin.name }}</span> <span class="coin-symbol">{{ coin.symbol|upper }}</span></td>
                        <td>${{ "%.2f"|format(coin.current_price) if coin.current_price < 1000 else "%.0f"|format(coin.current_price) }}</td>
                        <td class="{{ 'up' if coin.price_change_percentage_24h >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_24h) }}%</td>
                        <td class="{{ 'up' if coin.price_change_percentage_7d_in_currency >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_7d_in_currency) }}%</td>
                        <td class="mc">${{ "{:,.0f}".format(coin.market_cap) }}</td>
                        <td class="vol">${{ "{:,.0f}".format(coin.total_volume) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- News -->
        <h2 class="section-title" id="news">📰 Crypto News</h2>
        <div class="table-wrap">
            <ul class="news-list">
                {% for item in news %}
                <li>
                    <a href="{{ item.link }}" target="_blank" rel="noopener">{{ item.title }}</a>
                    <div class="news-date">{{ item.date[:25] if item.date else '' }}</div>
                </li>
                {% endfor %}
            </ul>
        </div>

        <!-- Features -->
        <h2 class="section-title" id="features">⚡ Everything You Need</h2>
        <div class="features-grid">
            <div class="feature-card"><div class="feature-icon">📊</div><h4>Real-Time Data</h4><p>Live prices, gas, and market caps for top coins.</p></div>
            <div class="feature-card"><div class="feature-icon">🔍</div><h4>Arbitrage Scanner</h4><p>Cross-DEX price disparities identified in real-time.</p></div>
            <div class="feature-card"><div class="feature-icon">⛽</div><h4>Gas Optimization</h4><p>Multi-chain gas tracker to minimize costs.</p></div>
            <div class="feature-card"><div class="feature-icon">🤖</div><h4>Telegram Bot</h4><p>Price alerts & portfolio tracking via Telegram.</p></div>
            <div class="feature-card"><div class="feature-icon">🔐</div><h4>Self-Custodial</h4><p>Your keys, your coins. No exchange risk.</p></div>
            <div class="feature-card"><div class="feature-icon">🔄</div><h4>Flash Loans</h4><p>Capital-free arbitrage via Aave V3 flash loans.</p></div>
        </div>

        <!-- Donation Section -->
        <div class="donation-box" id="donate">
            <h3>☕ Support Crypto Empire</h3>
            <p style="color: var(--muted); margin-bottom: 12px; font-size: 14px;">
                If you find this tool useful, send a tip in ETH, USDC, or any ERC-20 token.<br>
                Premium access (10K API req/day + arbitrage signals) — send 0.005 ETH (~$10).
            </p>
            <div class="chain-tags">
                <span class="chain-tag">Ethereum</span>
                <span class="chain-tag">Arbitrum</span>
                <span class="chain-tag">Base</span>
                <span class="chain-tag">Polygon</span>
                <span class="chain-tag">Optimism</span>
                <span class="chain-tag">BSC</span>
                <span class="chain-tag">Avalanche</span>
                <span class="chain-tag">Solana</span>
            </div>
            <div class="wallet-addr" onclick="copyWallet(this)">{{ wallet }}</div>
            <p style="color: var(--muted); font-size: 11px; margin-top: 6px;">Click to copy • All EVM chains supported</p>
        </div>

        <div style="text-align: center; margin-bottom: 24px;">
            <a href="https://github.com/ghassan-gaidi/crypto-empire" target="_blank" class="btn btn-outline" style="margin-right: 8px;">⭐ Star on GitHub</a>
            <a href="/docs" class="btn btn-outline">📖 API Docs</a>
        </div>

        <footer>
            <p>Built autonomously · <a href="https://github.com/ghassan-gaidi/crypto-empire">Open Source</a> · Zero KYC · Zero Budget</p>
            <p style="margin-top: 4px;">Wallet: <code style="font-size: 11px;">{{ wallet }}</code></p>
        </footer>
    </div>

    <div class="toast" id="toast">Copied! 📋</div>

    <script>
        function copyWallet(el) {
            navigator.clipboard.writeText(el.textContent).then(() => {
                const t = document.getElementById('toast');
                t.classList.add('show');
                setTimeout(() => t.classList.remove('show'), 2000);
            });
        }

        async function fetchGas() {
            try {
                const r = await fetch('/api/gas');
                const data = await r.json();
                for (const [chain, info] of Object.entries(data)) {
                    const el = document.getElementById('gas-' + (chain === 'ethereum' ? 'eth' : chain === 'polygon' ? 'poly' : chain === 'arbitrum' ? 'arb' : chain === 'base' ? 'base' : chain));
                    if (el && info.gas_gwei !== undefined) {
                        const gwei = info.gas_gwei;
                        el.textContent = gwei + ' gwei';
                        el.className = 'gwei ' + (gwei < 5 ? 'low' : gwei < 30 ? 'medium' : 'high');
                    }
                }
            } catch(e) {}
        }
        fetchGas();
        setInterval(fetchGas, 30000);
        setTimeout(() => location.reload(), 180000);
    </script>
</body>
</html>"""

# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    """Main dashboard"""
    # Top coins
    top_coins = {}
    for coin_id in ["bitcoin", "ethereum", "solana"]:
        data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true")
        if data and coin_id in data:
            top_coins[coin_id] = data[coin_id]

    # Market data with 7d change
    market_raw = fetch_sync(
        f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&price_change_percentage=7d"
    )
    market_data = market_raw if market_raw else []

    # Fear & Greed index
    fear_greed = None
    fg_data = fetch_sync("https://api.alternative.me/fng/?limit=1")
    if fg_data and "data" in fg_data and fg_data["data"]:
        fear_greed = {
            "value": fg_data["data"][0].get("value"),
            "classification": fg_data["data"][0].get("value_classification"),
        }

    # News
    news = fetch_rss("https://cointelegraph.com/rss")

    return render_template_string(
        INDEX_HTML,
        top_coins=top_coins,
        market_data=market_data,
        fear_greed=fear_greed,
        news=news,
        wallet=WALLET_ADDRESS,
    )


@app.route("/api/price/<coin_id>")
def api_price(coin_id):
    data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin_id in data:
        return jsonify({"coin": coin_id, "data": data[coin_id], "source": "coingecko"})
    return jsonify({"error": "Coin not found"}), 404


@app.route("/api/trending")
def api_trending():
    data = fetch_sync(f"{COINGECKO_API}/search/trending")
    if data and "coins" in data:
        coins = []
        for coin in data["coins"][:10]:
            item = coin.get("item", {})
            coins.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "market_cap_rank": item.get("market_cap_rank"),
                "price_btc": item.get("price_btc"),
                "score": item.get("score"),
            })
        return jsonify({"trending": coins})
    return jsonify({"error": "Could not fetch trending"}), 500


@app.route("/api/gas")
def api_gas():
    chains = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon": "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "base": "https://mainnet.base.org",
    }
    results = {}
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=6)
            data = r.json()
            if "result" in data:
                gwei = int(data["result"], 16) / 1e9
                results[name] = {"gas_gwei": round(gwei, 1)}
        except:
            results[name] = {"error": "unavailable"}
    return jsonify(results)


@app.route("/api/fear-greed")
def api_fear_greed():
    data = fetch_sync("https://api.alternative.me/fng/?limit=7")
    if data and "data" in data:
        return jsonify(data["data"])
    return jsonify({"error": "unavailable"}), 500


@app.route("/api/news")
def api_news():
    news = fetch_rss("https://cointelegraph.com/rss")
    return jsonify(news)


@app.route("/api/wallet")
def api_wallet():
    chains = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon": "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "base": "https://mainnet.base.org",
    }
    results = {}
    for name, url in chains.items():
        try:
            r = requests.post(url, json={
                "jsonrpc":"2.0","method":"eth_getBalance",
                "params":[WALLET_ADDRESS, "latest"],"id":1
            }, timeout=6)
            data = r.json()
            if "result" in data:
                bal = int(data["result"], 16) / 1e18
                results[name] = {"balance": bal}
        except:
            results[name] = {"balance": None}
    return jsonify({"wallet": WALLET_ADDRESS, "balances": results})


@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "wallet": WALLET_ADDRESS,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/docs")
def docs():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Empire — API Docs</title>
    <style>
        :root { --bg: #0a0b0e; --card: #13151a; --border: #1e2030; --accent: #00d4aa; --text: #e2e8f0; --muted: #64748b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: var(--accent); margin-bottom: 8px; }
        h2 { color: var(--accent); margin: 24px 0 12px; }
        p { color: var(--muted); margin-bottom: 16px; }
        .endpoint { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; }
        .method { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; margin-right: 8px; background: #22c55e; color: #000; }
        .url { font-family: monospace; font-size: 14px; color: var(--accent); }
        .desc { color: var(--muted); font-size: 13px; margin-top: 4px; }
        pre { background: #0a0b0e; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; margin-top: 8px; }
        a { color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" style="color: var(--muted); font-size: 14px;">← Back to Dashboard</a>
        <h1>Crypto Empire API</h1>
        <p>Free public API for crypto data. No auth required.</p>
        
        <div style="background:#1e2030;padding:12px;border-radius:8px;margin:16px 0;">
            <strong>🆓 Free:</strong> 100 req/day · 
            <strong>💎 Premium:</strong> 10K req/day (send 0.005 ETH to wallet)
        </div>

        <div class="endpoint"><span class="method">GET</span><span class="url">/api/price/&lt;coin_id&gt;</span><div class="desc">Get current price.</div><pre>curl https://crypto-empire-ten.vercel.app/api/price/bitcoin</pre></div>
        <div class="endpoint"><span class="method">GET</span><span class="url">/api/trending</span><div class="desc">Trending coins.</div><pre>curl https://crypto-empire-ten.vercel.app/api/trending</pre></div>
        <div class="endpoint"><span class="method">GET</span><span class="url">/api/gas</span><div class="desc">Gas prices across chains.</div><pre>curl https://crypto-empire-ten.vercel.app/api/gas</pre></div>
        <div class="endpoint"><span class="method">GET</span><span class="url">/api/wallet</span><div class="desc">Wallet balances.</div><pre>curl https://crypto-empire-ten.vercel.app/api/wallet</pre></div>
        <div class="endpoint"><span class="method">GET</span><span class="url">/api/fear-greed</span><div class="desc">Fear & Greed index.</div><pre>curl https://crypto-empire-ten.vercel.app/api/fear-greed</pre></div>
        <div class="endpoint"><span class="method">GET</span><span class="url">/api/news</span><div class="desc">Latest crypto news.</div><pre>curl https://crypto-empire-ten.vercel.app/api/news</pre></div>
        <div class="endpoint"><span class="method">GET</span><span class="url">/api/health</span><div class="desc">Health check.</div></div>

        <p style="margin-top:24px;">Support: <code style="color:var(--accent);">{{ wallet }}</code></p>
        <p><a href="https://github.com/ghassan-gaidi/crypto-empire">GitHub</a></p>
    </div>
</body>
</html>""", wallet=WALLET_ADDRESS)


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"⚡ Crypto Empire Dashboard starting on port {port}")
    print(f"💰 Wallet: {WALLET_ADDRESS}")
    app.run(host="0.0.0.0", port=port, debug=debug)
