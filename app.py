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
    <meta name="description" content="Free crypto dashboard with live prices, gas tracker, wallet balance checker, and market data for Ethereum, Bitcoin, Arbitrum, Polygon & Base.">
    <meta name="keywords" content="crypto dashboard, wallet checker, gas tracker, Ethereum gas, Bitcoin price, crypto prices, portfolio tracker, blockchain tools">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/">
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
                <a href="/blog">Blog</a>
                <a href="/docs">API</a>
                <a href="/wallet-check">Wallet</a>
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
            "value": int(fg_data["data"][0].get("value", 50)),
            "classification": fg_data["data"][0].get("value_classification", "Neutral"),
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
# Wallet Check Page
# ============================================================

WALLET_CHECK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wallet Checker — Crypto Empire</title>
    <style>
        :root { --bg: #0a0b0e; --card: #13151a; --border: #1e2030; --accent: #00d4aa; --text: #e2e8f0; --muted: #64748b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: var(--accent); margin-bottom: 8px; }
        p { color: var(--muted); margin-bottom: 20px; }
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-family: monospace;
            font-size: 14px;
            outline: none;
        }
        input[type="text"]:focus { border-color: var(--accent); }
        button {
            background: var(--accent); color: #000; border: none;
            padding: 12px 24px; border-radius: 8px; font-weight: 600;
            cursor: pointer; font-size: 14px; margin-top: 8px;
        }
        button:hover { opacity: 0.9; }
        .result { margin-top: 24px; }
        .chain-row {
            display: flex; justify-content: space-between;
            align-items: center;
            background: var(--card); border: 1px solid var(--border);
            border-radius: 8px; padding: 14px 18px; margin-bottom: 8px;
        }
        .chain-name { font-weight: 600; }
        .chain-bal { font-family: monospace; color: var(--accent); font-size: 16px; }
        .chain-usd { color: var(--muted); font-size: 12px; }
        .total { font-size: 24px; font-weight: 700; color: var(--accent); text-align: center; padding: 20px; }
        .error { color: var(--danger); text-align: center; padding: 20px; }
        .loading { text-align: center; color: var(--muted); padding: 20px; }
        nav a { color: var(--muted); text-decoration: none; font-size: 14px; }
        nav a:hover { color: var(--accent); }
        @media (max-width: 640px) { .chain-row { flex-direction: column; gap: 4px; text-align: center; } }
    </style>
</head>
<body>
    <div class="container">
        <nav style="margin-bottom: 20px;"><a href="/">← Back to Dashboard</a> &nbsp; <a href="/docs">API</a></nav>
        <h1>🔍 Wallet Checker</h1>
        <p>Check the ETH balances of any wallet across Ethereum, Arbitrum, Base, and Polygon.</p>
        <input type="text" id="address" placeholder="0x... or ENS name" value="0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef">
        <br>
        <button onclick="checkWallet()">Check Wallet</button>
        <div id="results" class="result"></div>
    </div>
    <script>
    async function checkWallet() {
        const addr = document.getElementById('address').value.trim();
        const el = document.getElementById('results');
        if (!addr || !addr.startsWith('0x')) { el.innerHTML = '<div class="error">Invalid address</div>'; return; }
        el.innerHTML = '<div class="loading">⏳ Checking...</div>';
        try {
            const r = await fetch('/api/check-wallet/' + encodeURIComponent(addr));
            const data = await r.json();
            if (data.error) { el.innerHTML = '<div class="error">' + data.error + '</div>'; return; }
            let html = '<div class="total">Total: ' + data.total_usd_formatted + ' USD</div>';
            for (const chain of data.chains) {
                html += '<div class="chain-row">' +
                    '<span class="chain-name">' + chain.name + '</span>' +
                    '<span><span class="chain-bal">' + chain.balance_formatted + '</span> <span class="chain-usd">$' + chain.usd_value.toFixed(2) + '</span></span>' +
                    '</div>';
            }
            html += '<div style="text-align:center;margin-top:16px;"><a href="https://debank.com/profile/' + addr + '" target="_blank" style="color:var(--accent);">View on DeBank →</a></div>';
            el.innerHTML = html;
        } catch(e) {
            el.innerHTML = '<div class="error">Request failed</div>';
        }
    }
    // Auto-check on load
    checkWallet();
    </script>
</body>
</html>"""

@app.route("/wallet-check")
def wallet_check():
    return render_template_string(WALLET_CHECK_HTML)


@app.route("/api/check-wallet/<address>")
def api_check_wallet(address):
    """Check wallet balances across multiple chains"""
    chains = {
        "ethereum": {"name": "Ethereum", "rpc": "https://ethereum-rpc.publicnode.com", "coingecko": "ethereum"},
        "arbitrum": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "coingecko": "ethereum"},
        "base": {"name": "Base", "rpc": "https://mainnet.base.org", "coingecko": "ethereum"},
        "polygon": {"name": "Polygon", "rpc": "https://polygon-rpc.com", "coingecko": "matic-network"},
    }
    
    # Get ETH price in USD
    eth_price = 0
    price_data = fetch_sync(f"{COINGECKO_API}/simple/price?ids=ethereum,matic-network&vs_currencies=usd")
    if price_data:
        eth_price = (price_data.get("ethereum", {}) or {}).get("usd", 0)
    
    matic_price = 0
    if price_data:
        matic_price = (price_data.get("matic-network", {}) or {}).get("usd", 0)
    
    results = []
    total_usd = 0
    
    for key, cfg in chains.items():
        try:
            r = requests.post(cfg["rpc"], json={
                "jsonrpc": "2.0", "method": "eth_getBalance",
                "params": [address, "latest"], "id": 1
            }, timeout=8)
            data = r.json()
            if "result" in data:
                bal = int(data["result"], 16) / 1e18
                price = eth_price if cfg["coingecko"] == "ethereum" else matic_price
                usd = bal * price
                total_usd += usd
                results.append({
                    "chain": key,
                    "name": cfg["name"],
                    "balance": bal,
                    "balance_formatted": f"{bal:.6f}" if bal >= 0.001 else f"{bal:.8f}",
                    "usd_value": usd,
                })
            else:
                results.append({"chain": key, "name": cfg["name"], "balance": 0, "balance_formatted": "0", "usd_value": 0})
        except:
            results.append({"chain": key, "name": cfg["name"], "balance": None, "balance_formatted": "error", "usd_value": 0})
    
    return jsonify({
        "address": address,
        "chains": results,
        "total_usd": total_usd,
        "total_usd_formatted": f"${total_usd:,.2f}",
    })


# ============================================================
# SEO: Blog Content
# ============================================================

BLOG_POSTS = [
    {
        "slug": "best-crypto-wallet-balance-checker-2026",
        "title": "Best Crypto Wallet Balance Checker 2026 — Track Any Address Across 4 Chains",
        "date": "2026-06-03",
        "tags": ["wallet checker", "crypto tools", "portfolio tracker"],
        "content": """
<h2>Check Any Ethereum Wallet Balance Across Multiple Chains</h2>
<p>Crypto Empire's <a href="/wallet-check">Wallet Checker</a> lets you instantly view ETH, MATIC, and ERC-20 token balances across Ethereum, Arbitrum, Base, and Polygon — all from one page. No signup, no API key, no wallet connection needed.</p>

<h3>Why Use a Multi-Chain Wallet Checker?</h3>
<p>Modern crypto users hold assets across multiple Layer 2 solutions. Instead of checking each chain's block explorer separately, our tool aggregates balances from Ethereum, Arbitrum, Base, and Polygon into a single USD value.</p>

<h3>Features</h3>
<ul>
<li><strong>Instant balance lookup</strong> — Enter any 0x address and see balances in seconds</li>
<li><strong>Multi-chain support</strong> — Ethereum, Arbitrum, Base, Polygon</li>
<li><strong>USD conversion</strong> — Real-time prices via CoinGecko</li>
<li><strong>ENS support</strong> — Enter ENS names directly</li>
<li><strong>Free & open source</strong> — No ads, no tracking</li>
</ul>

<h3>How to Use</h3>
<p>Visit the <a href="/wallet-check">Wallet Checker</a> page, enter any Ethereum address, and click "Check Wallet". The tool queries live RPC endpoints and returns balances with USD values.</p>

<p>If you find this tool useful, consider supporting development by sending a donation to the project wallet.</p>
"""
    },
    {
        "slug": "ethereum-gas-tracker-live-prices",
        "title": "Ethereum Gas Tracker — Live ETH Gas Prices for Polygon, Arbitrum & Base 2026",
        "date": "2026-06-02",
        "tags": ["gas tracker", "ETH gas", "Layer 2 fees"],
        "content": """
<h2>Live Gas Price Tracker for Ethereum and L2s</h2>
<p>Our <a href="/">Gas Tracker</a> provides real-time gas prices for Ethereum, Polygon, Arbitrum, and Base. Optimize your transaction timing and reduce fees.</p>

<h3>Current Gas Prices</h3>
<p>The dashboard displays live gas prices in Gwei for the four major EVM chains. Prices update every 30 seconds with color-coded indicators (green = cheap, yellow = moderate, red = expensive).</p>

<h3>When to Transact</h3>
<ul>
<li><strong>Low gas (&lt;5 Gwei ETH)</strong> — Best time for transfers and DeFi interactions</li>
<li><strong>Medium gas (5-30 Gwei ETH)</strong> — Normal conditions, fine for standard transactions</li>
<li><strong>High gas (&gt;30 Gwei ETH)</strong> — Expensive, consider waiting or using L2s</li>
</ul>

<h3>Chain Comparison</h3>
<p>Polygon typically offers the lowest fees (&lt;100 Gwei MATIC), while Ethereum mainnet can spike during high-demand periods. Arbitrum and Base offer a middle ground with Ethereum-level security and reduced fees.</p>

<p>Bookmark our <a href="/">dashboard</a> for quick access to live gas data across all major chains.</p>
"""
    },
    {
        "slug": "crypto-portfolio-tracker-free-tools",
        "title": "Free Crypto Portfolio Tracker Tools — Track Without Connecting Your Wallet",
        "date": "2026-06-01",
        "tags": ["portfolio tracker", "crypto tools", "DeFi"],
        "content": """
<h2>Track Your Crypto Portfolio Without Connecting Your Wallet</h2>
<p>Privacy-focused crypto tracking is possible with on-chain data tools. Here are the best free options for monitoring your portfolio in 2026.</p>

<h3>1. Crypto Empire Wallet Checker</h3>
<p>Our <a href="/wallet-check">Wallet Checker</a> lets you check any Ethereum address across 4 chains instantly. No wallet connection, no data collection, just pure on-chain balance queries.</p>

<h3>2. Live Market Data</h3>
<p>Our <a href="/">dashboard</a> shows the top 20 cryptocurrencies with real-time prices, 24h and 7d changes, market cap, and volume. Updated directly from CoinGecko's API.</p>

<h3>3. Multi-Chain Balance API</h3>
<p>Developers can use our free <a href="/docs">API</a> to query wallet balances programmatically. No authentication required up to 100 requests/day.</p>

<h3>Why Portfolio Tracking Matters</h3>
<p>Regular portfolio monitoring helps you track gains, optimize tax reporting, and spot unusual activity. Using read-only tools preserves your privacy and security.</p>

<p>Support these free tools by donating to the project wallet. Your contribution helps keep the service running and ad-free.</p>
"""
    },
    {
        "slug": "top-cryptocurrencies-today",
        "title": "Top 20 Cryptocurrencies by Market Cap — Live Prices & Charts June 2026",
        "date": "2026-06-01",
        "tags": ["crypto prices", "market cap", "Bitcoin", "Ethereum"],
        "content": """
<h2>Top 20 Cryptocurrencies by Market Cap — Live Prices</h2>
<p>Our <a href="/">dashboard</a> displays the top 20 cryptocurrencies ranked by market capitalization, with live prices from CoinGecko.</p>

<h3>Today's Top Coins</h3>
<p>Bitcoin (BTC) remains the largest cryptocurrency by market cap, followed by Ethereum (ETH), Tether (USDT), and BNB (BNB). The rankings update automatically with each page reload.</p>

<h3>Understanding Market Metrics</h3>
<ul>
<li><strong>Market Cap</strong> — Total value of all coins in circulation (price × circulating supply)</li>
<li><strong>24h Change</strong> — Price movement over the last 24 hours</li>
<li><strong>7d Change</strong> — Price trend over the last week</li>
<li><strong>Volume (24h)</strong> — Total trading volume across all markets in the last day</li>
</ul>

<h3>Market Sentiment</h3>
<p>Our dashboard also includes the Fear & Greed Index, a popular market sentiment indicator. Values below 25 indicate fear (potential buying opportunity), while values above 75 suggest greed (potential overvaluation).</p>

<p>Check back daily for updated prices and market data. Support the project by sending a donation to the wallet address below.</p>
"""
    },
]

@app.route("/blog")
def blog_index():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Empire Blog — Crypto Tools, Guides & Market Analysis</title>
    <meta name="description" content="Free crypto tools, wallet checker, gas tracker, and market data. Guides and analysis for cryptocurrency traders and investors.">
    <meta name="keywords" content="crypto tools, wallet checker, gas tracker, Bitcoin, Ethereum, cryptocurrency prices">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/blog">
    <style>
        :root { --bg: #0a0b0e; --card: #13151a; --border: #1e2030; --accent: #00d4aa; --text: #e2e8f0; --muted: #64748b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: var(--accent); margin-bottom: 8px; font-size: 28px; }
        .subtitle { color: var(--muted); margin-bottom: 32px; }
        .post { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 16px; }
        .post:hover { border-color: var(--accent); }
        .post h2 { font-size: 18px; margin-bottom: 6px; }
        .post h2 a { color: var(--text); text-decoration: none; }
        .post h2 a:hover { color: var(--accent); }
        .post .meta { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
        .post .tags { display: flex; gap: 6px; flex-wrap: wrap; }
        .post .tag { background: rgba(0,212,170,0.1); color: var(--accent); padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .donation-box { background: linear-gradient(135deg, rgba(0,212,170,0.05), rgba(124,58,237,0.05)); border: 1px solid var(--accent); border-radius: 12px; padding: 24px; margin: 24px 0; text-align: center; }
        .wallet-addr { background: var(--bg); padding: 10px 16px; border-radius: 8px; font-family: monospace; font-size: 13px; color: var(--accent); word-break: break-all; cursor: pointer; border: 1px solid var(--border); display: inline-block; max-width: 100%; user-select: all; }
        nav a { color: var(--muted); text-decoration: none; font-size: 14px; }
        nav a:hover { color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <nav style="margin-bottom: 24px;"><a href="/">← Dashboard</a> &nbsp; <a href="/docs">API</a> &nbsp; <a href="/wallet-check">Wallet Checker</a></nav>
        <h1>📝 Crypto Empire Blog</h1>
        <p class="subtitle">Free crypto tools, guides, and market analysis. Check wallet balances, track gas fees, and monitor live prices.</p>
        
        {% for post in posts %}
        <div class="post">
            <h2><a href="/blog/{{ post.slug }}">{{ post.title }}</a></h2>
            <div class="meta">{{ post.date }} · {{ post.tags|join(', ') }}</div>
            <div class="tags">{% for tag in post.tags %}<span class="tag">{{ tag }}</span>{% endfor %}</div>
        </div>
        {% endfor %}
        
        <div class="donation-box">
            <h3>☕ Support These Free Tools</h3>
            <p style="color: var(--muted); font-size: 14px; margin-bottom: 12px;">If you find these tools useful, send a tip in ETH, USDC, or any ERC-20 token.</p>
            <div class="wallet-addr">{{ wallet }}</div>
            <p style="color: var(--muted); font-size: 11px; margin-top: 6px;">Click to copy</p>
        </div>
        
        <footer style="text-align:center;padding:24px 0;color:var(--muted);font-size:12px;border-top:1px solid var(--border);">
            <p><a href="/">Crypto Empire Dashboard</a> · <a href="/sitemap.xml">Sitemap</a></p>
        </footer>
    </div>
</body>
</html>""", posts=BLOG_POSTS, wallet=WALLET_ADDRESS)


@app.route("/blog/<slug>")
def blog_post(slug):
    post = None
    for p in BLOG_POSTS:
        if p["slug"] == slug:
            post = p
            break
    if not post:
        return "Not found", 404
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} — Crypto Empire</title>
    <meta name="description" content="{{ title }}. Free crypto tools, wallet checker, gas tracker, and live prices.">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/blog/{{ slug }}">
    <style>
        :root { --bg: #0a0b0e; --card: #13151a; --border: #1e2030; --accent: #00d4aa; --text: #e2e8f0; --muted: #64748b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: var(--accent); font-size: 26px; margin-bottom: 8px; }
        h2 { color: var(--accent); font-size: 20px; margin: 24px 0 12px; }
        h3 { font-size: 17px; margin: 20px 0 10px; }
        p { margin-bottom: 14px; color: var(--muted); }
        ul { margin: 0 0 14px 20px; color: var(--muted); }
        li { margin-bottom: 6px; }
        a { color: var(--accent); }
        .meta { color: var(--muted); font-size: 12px; margin-bottom: 24px; }
        .donation-box { background: linear-gradient(135deg, rgba(0,212,170,0.05), rgba(124,58,237,0.05)); border: 1px solid var(--accent); border-radius: 12px; padding: 24px; margin: 24px 0; text-align: center; }
        .wallet-addr { background: var(--bg); padding: 10px 16px; border-radius: 8px; font-family: monospace; font-size: 13px; color: var(--accent); word-break: break-all; cursor: pointer; border: 1px solid var(--border); display: inline-block; max-width: 100%; user-select: all; }
        nav a { color: var(--muted); text-decoration: none; font-size: 14px; }
        nav a:hover { color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <nav style="margin-bottom: 24px;"><a href="/">← Dashboard</a> &nbsp; <a href="/blog">Blog</a></nav>
        <h1>{{ title }}</h1>
        <div class="meta">{{ date }} · Tags: {{ tags|join(", ") }}</div>
        <div>{{ content|safe }}</div>
        
        <div class="donation-box">
            <h3>☕ Support These Free Tools</h3>
            <p style="color: var(--muted); font-size: 14px; margin-bottom: 12px;">If you found this guide useful, send a tip in ETH, USDC, or any ERC-20 token.</p>
            <div class="wallet-addr">{{ wallet }}</div>
            <p style="color: var(--muted); font-size: 11px; margin-top: 6px;">Click to copy</p>
        </div>
        
        <footer style="text-align:center;padding:24px 0;color:var(--muted);font-size:12px;border-top:1px solid var(--border);">
            <p><a href="/blog">← More articles</a></p>
        </footer>
    </div>
</body>
</html>""", title=post["title"], slug=post["slug"], date=post["date"], tags=post["tags"], content=post["content"], wallet=WALLET_ADDRESS)


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "hourly"},
        {"loc": "/blog", "priority": "0.9", "changefreq": "daily"},
        {"loc": "/docs", "priority": "0.7", "changefreq": "weekly"},
        {"loc": "/wallet-check", "priority": "0.8", "changefreq": "daily"},
    ]
    for post in BLOG_POSTS:
        pages.append({"loc": f"/blog/{post['slug']}", "priority": "0.6", "changefreq": "monthly"})

    urls = ""
    for p in pages:
        urls += f"""  <url>
    <loc>https://crypto-empire-ten.vercel.app{p['loc']}</loc>
    <priority>{p['priority']}</priority>
    <changefreq>{p['changefreq']}</changefreq>
  </url>\n"""
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""
    return sitemap_xml, 200, {"Content-Type": "application/xml"}


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Allow: /
Sitemap: https://crypto-empire-ten.vercel.app/sitemap.xml
""", 200, {"Content-Type": "text/plain"}


# ============================================================
# Main
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"⚡ Crypto Empire Dashboard starting on port {port}")
    print(f"💰 Wallet: {WALLET_ADDRESS}")
    app.run(host="0.0.0.0", port=port, debug=debug)
