#!/usr/bin/env python3
"""
Crypto Empire - Web Dashboard & API
Autonomous crypto intelligence platform with monetization
"""
import os
import json
import time
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from functools import wraps
from urllib.parse import quote

from flask import Flask, render_template_string, jsonify, request, redirect, url_for, session, send_from_directory
from flask_cors import CORS
import requests

# ============================================================
# Configuration
# ============================================================
WALLET_ADDRESS = "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef"
# Use /tmp on Vercel (serverless), otherwise use home dir
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
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            usage_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS price_cache (
            coin_id TEXT PRIMARY KEY,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            page TEXT DEFAULT '/',
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS wallet_trackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE,
            label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# CoinGecko API helpers
# ============================================================
COINGECKO_API = "https://api.coingecko.com/api/v3"
CACHE_TTL = 60  # seconds

def get_cached_or_fetch(url, cache_key=None):
    """Fetch with caching"""
    if not cache_key:
        cache_key = url
    # Check cache
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    cached = c.execute("SELECT data, updated_at FROM price_cache WHERE coin_id=?", (cache_key,)).fetchone()
    if cached:
        data, updated = cached
        age = (datetime.now() - datetime.fromisoformat(updated)).total_seconds()
        if age < CACHE_TTL:
            conn.close()
            return json.loads(data)
    # Fetch fresh
    try:
        resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            data = resp.json()
            c.execute("INSERT OR REPLACE INTO price_cache (coin_id, data, updated_at) VALUES (?, ?, ?)",
                      (cache_key, json.dumps(data), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return data
    except:
        pass
    conn.close()
    return None

def fetch_sync(url):
    """Simple fetch"""
    try:
        resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

# ============================================================
# HTML Template — Dark, modern, feature-rich
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
            margin-bottom: 40px;
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
        
        .hero {
            text-align: center;
            padding: 40px 0 30px;
        }
        .hero h1 {
            font-size: clamp(28px, 5vw, 48px);
            font-weight: 800;
            margin-bottom: 16px;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero p { font-size: 18px; color: var(--muted); max-width: 600px; margin: 0 auto 24px; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 40px; }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: var(--accent); }
        .card h3 { font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .card .value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
        .card .change { font-size: 14px; }
        .up { color: var(--success); }
        .down { color: var(--danger); }
        
        .table-wrap {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 30px;
        }
        .table-wrap h2 {
            padding: 20px 24px;
            font-size: 16px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid var(--border);
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 24px; text-align: left; font-size: 14px; }
        th { color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--border); }
        td { border-bottom: 1px solid rgba(30, 32, 48, 0.5); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(0, 212, 170, 0.03); }
        .rank { color: var(--muted); }
        .coin-name { font-weight: 600; }
        .coin-symbol { color: var(--muted); font-size: 12px; }
        .mc, .vol { color: var(--muted); }
        
        .donation-section {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
            text-align: center;
        }
        .donation-section h3 { color: var(--accent); font-size: 18px; margin-bottom: 12px; }
        .wallet-addr {
            background: var(--bg);
            padding: 12px 16px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            color: var(--accent);
            word-break: break-all;
            cursor: pointer;
            border: 1px solid var(--border);
            display: inline-block;
            max-width: 100%;
        }
        .wallet-addr:hover { border-color: var(--accent); }
        .chains { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin: 12px 0; }
        .chain-tag {
            background: var(--bg);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            color: var(--muted);
            border: 1px solid var(--border);
        }

        .gas-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 30px; }
        .gas-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        .gas-card .chain { font-size: 13px; color: var(--muted); margin-bottom: 4px; }
        .gas-card .gwei { font-size: 22px; font-weight: 700; }
        .gas-card .low { color: var(--success); }
        .gas-card .medium { color: var(--warning); }
        .gas-card .high { color: var(--danger); }

        .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 40px; }
        .feature-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: border-color 0.2s;
        }
        .feature-card:hover { border-color: var(--accent2); }
        .feature-icon { font-size: 32px; margin-bottom: 8px; }
        .feature-card h4 { font-size: 16px; margin-bottom: 6px; }
        .feature-card p { font-size: 13px; color: var(--muted); }

        footer {
            text-align: center;
            padding: 30px 0;
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 13px;
        }
        footer a { color: var(--accent); text-decoration: none; }

        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-dot.online { background: var(--success); box-shadow: 0 0 8px var(--success); }

        @media (max-width: 640px) {
            .container { padding: 12px; }
            header .container { flex-direction: column; }
            .hero h1 { font-size: 28px; }
            th, td { padding: 8px 12px; }
        }

        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: #000;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 100;
        }
        .toast.show { opacity: 1; }

        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 30px; }
        .pricing-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
        }
        .pricing-card.featured { border-color: var(--accent); position: relative; }
        .pricing-card.featured::before {
            content: 'BEST VALUE';
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: #000;
            padding: 2px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
        }
        .pricing-card h3 { font-size: 18px; margin-bottom: 8px; }
        .pricing-card .price { font-size: 32px; font-weight: 800; margin-bottom: 4px; }
        .pricing-card .price-sub { font-size: 13px; color: var(--muted); margin-bottom: 16px; }
        .pricing-card ul { list-style: none; text-align: left; margin-bottom: 20px; }
        .pricing-card ul li { padding: 6px 0; font-size: 13px; color: var(--muted); }
        .pricing-card ul li::before { content: '✓ '; color: var(--success); }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">Crypto <span>Empire</span></a>
            <nav>
                <a href="#market">Market</a>
                <a href="#gas">Gas</a>
                <a href="#features">Features</a>
                <a href="#pricing">Pricing</a>
                <a href="/docs">API</a>
                <a href="https://github.com/ghassan-gaidi/crypto-empire" target="_blank">GitHub</a>
                <a class="btn btn-sm" href="#donate">Support</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <section class="hero">
            <h1>Autonomous Crypto Intelligence</h1>
            <p>Real-time market data, gas tracking, arbitrage detection & automated trading — all self-custodial and open source.</p>
            <div style="margin-bottom: 12px;">
                <span class="status-dot online"></span>
                <span style="color: var(--muted); font-size: 13px;">System Uptime: Active · Wallet: <code style="color: var(--accent); font-size: 12px;">{{ wallet[:10] }}...{{ wallet[-6:] }}</code></span>
            </div>
        </section>

        <!-- Top Coins -->
        <div class="grid" id="market">
            {% for coin_id, data in top_coins.items() %}
            <div class="card">
                <h3>{{ coin_id|upper }}</h3>
                <div class="value">${{ "%.2f"|format(data.usd) if data.usd < 1000 else "%.0f"|format(data.usd) }}</div>
                <div class="change {{ 'up' if data.usd_24h_change >= 0 else 'down' }}">
                    {{ "%.2f"|format(data.usd_24h_change) }}%
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Gas Tracker -->
        <h2 style="font-size: 16px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;" id="gas">⛽ Gas Tracker</h2>
        <div class="gas-grid" id="gas-grid">
            <div class="gas-card"><div class="chain">Ethereum</div><div class="gwei low" id="gas-eth">—</div></div>
            <div class="gas-card"><div class="chain">Polygon</div><div class="gwei medium" id="gas-poly">—</div></div>
            <div class="gas-card"><div class="chain">Arbitrum</div><div class="gwei high" id="gas-arb">—</div></div>
            <div class="gas-card"><div class="chain">Base</div><div class="gwei" id="gas-base" style="color: var(--accent);">—</div></div>
        </div>

        <!-- Market Table -->
        <div class="table-wrap">
            <h2>📊 Market Overview</h2>
            <table>
                <thead>
                    <tr><th>#</th><th>NAME</th><th>PRICE</th><th>24H</th><th>MARKET CAP</th><th>VOLUME (24H)</th></tr>
                </thead>
                <tbody>
                    {% for coin in market_data %}
                    <tr>
                        <td class="rank">{{ coin.market_cap_rank }}</td>
                        <td><span class="coin-name">{{ coin.name }}</span> <span class="coin-symbol">{{ coin.symbol|upper }}</span></td>
                        <td>${{ "%.2f"|format(coin.current_price) if coin.current_price < 1000 else "%.0f"|format(coin.current_price) }}</td>
                        <td class="{{ 'up' if coin.price_change_percentage_24h >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_24h) }}%</td>
                        <td class="mc">${{ "{:,.0f}".format(coin.market_cap) }}</td>
                        <td class="vol">${{ "{:,.0f}".format(coin.total_volume) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Features -->
        <h2 style="font-size: 16px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;" id="features">⚡ Everything You Need</h2>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h4>Real-Time Market Data</h4>
                <p>Prices, volumes, and market caps for top 100 coins. Updated every 60 seconds.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <h4>Arbitrage Detection</h4>
                <p>Cross-exchange and cross-chain price disparities identified in real-time.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⛽</div>
                <h4>Gas Optimization</h4>
                <p>Multi-chain gas tracker to minimize transaction costs.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <h4>Telegram Bot</h4>
                <p>Price alerts, portfolio tracking, and premium signals via Telegram.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔐</div>
                <h4>Self-Custodial</h4>
                <p>Your keys, your coins. No exchange risk. Everything is on-chain verifiable.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔄</div>
                <h4>Flash Loans</h4>
                <p>Capital-free arbitrage through Aave V3 flash loans. Deployed on Ethereum.</p>
            </div>
        </div>

        <!-- Pricing -->
        <h2 style="font-size: 16px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;" id="pricing">💰 Simple Pricing</h2>
        <div class="pricing-grid">
            <div class="pricing-card">
                <h3>Free</h3>
                <div class="price">$0</div>
                <div class="price-sub">Forever</div>
                <ul>
                    <li>Market data & charts</li>
                    <li>Gas tracker</li>
                    <li>100 API req/day</li>
                    <li>Public Telegram alerts</li>
                </ul>
                <a href="/" class="btn btn-outline">Get Started</a>
            </div>
            <div class="pricing-card featured">
                <h3>Premium</h3>
                <div class="price">$10</div>
                <div class="price-sub">/month or ~0.005 ETH</div>
                <ul>
                    <li>Real-time arbitrage signals</li>
                    <li>Portfolio tracking</li>
                    <li>10,000 API req/day</li>
                    <li>Priority Telegram alerts</li>
                    <li>Flash loan strategies</li>
                </ul>
                <a href="#donate" class="btn">Subscribe Now</a>
            </div>
            <div class="pricing-card">
                <h3>Lifetime</h3>
                <div class="price">$50</div>
                <div class="price-sub">One-time payment</div>
                <ul>
                    <li>All Premium features</li>
                    <li>Unlimited API access</li>
                    <li>Early access to new features</li>
                    <li>Direct support</li>
                </ul>
                <a href="#donate" class="btn btn-purple">Get Lifetime</a>
            </div>
        </div>

        <!-- Donation / Payment Section -->
        <div class="donation-section" id="donate">
            <h3>🪙 Pay with Crypto</h3>
            <p style="color: var(--muted); margin-bottom: 16px;">
                Send ETH, USDC, USDT, or any ERC-20 to the address below.<br>
                <strong>Premium Monthly (~$10):</strong> Send 0.005 ETH · <strong>Lifetime (~$50):</strong> Send 0.025 ETH
            </p>
            <div class="chains">
                <span class="chain-tag">Ethereum</span>
                <span class="chain-tag">Arbitrum</span>
                <span class="chain-tag">Base</span>
                <span class="chain-tag">Polygon</span>
                <span class="chain-tag">Optimism</span>
                <span class="chain-tag">BSC</span>
                <span class="chain-tag">Avalanche</span>
            </div>
            <div class="wallet-addr" onclick="copyWallet(this)" title="Click to copy">{{ wallet }}</div>
            <p style="color: var(--muted); font-size: 12px; margin-top: 8px;">All major EVM chains supported · Self-custodial wallet</p>
        </div>

        <!-- GitHub Stars / Social Proof -->
        <div style="text-align: center; margin-bottom: 30px;">
            <a href="https://github.com/ghassan-gaidi/crypto-empire" target="_blank" class="btn btn-outline" style="margin-right: 8px;">⭐ Star on GitHub</a>
            <a href="/docs" class="btn btn-outline">📖 API Docs</a>
        </div>

        <footer>
            <p>Built with ❤️ for the autonomous crypto economy · <a href="https://github.com/ghassan-gaidi/crypto-empire">Open Source</a></p>
            <p style="margin-top: 4px;">Wallet: <code style="font-size: 11px;">{{ wallet }}</code></p>
        </footer>
    </div>

    <div class="toast" id="toast">Copied! 📋</div>

    <script>
        // Copy wallet address
        function copyWallet(el) {
            navigator.clipboard.writeText(el.textContent).then(() => {
                const t = document.getElementById('toast');
                t.classList.add('show');
                setTimeout(() => t.classList.remove('show'), 2000);
            });
        }

        // Fetch gas prices
        async function fetchGas() {
            try {
                const r = await fetch('/api/gas');
                const data = await r.json();
                const els = {
                    'eth': document.getElementById('gas-eth'),
                    'poly': document.getElementById('gas-poly'),
                    'arb': document.getElementById('gas-arb'),
                    'base': document.getElementById('gas-base'),
                };
                if (data.ethereum && data.ethereum.gas_gwei) {
                    els.eth.textContent = data.ethereum.gas_gwei + ' gwei';
                    els.eth.className = 'gwei ' + (data.ethereum.gas_gwei < 30 ? 'low' : data.ethereum.gas_gwei < 80 ? 'medium' : 'high');
                }
                if (data.polygon && data.polygon.gas_gwei) {
                    els.poly.textContent = data.polygon.gas_gwei + ' gwei';
                }
                // For chains without native gas oracles, estimate
                if (data.arbitrum && data.arbitrum.gas_gwei) {
                    els.arb.textContent = data.arbitrum.gas_gwei + ' gwei';
                }
                if (data.base && data.base.gas_gwei) {
                    els.base.textContent = data.base.gas_gwei + ' gwei';
                }
            } catch(e) {}
        }
        fetchGas();
        setInterval(fetchGas, 30000);

        // Auto-refresh market data
        setTimeout(() => location.reload(), 120000);
    </script>
</body>
</html>"""

# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    """Main dashboard page"""
    top_coins = {}
    for coin_id in ["bitcoin", "ethereum", "solana"]:
        data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true")
        if data and coin_id in data:
            top_coins[coin_id] = data[coin_id]

    market_raw = fetch_sync(f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1")
    market_data = market_raw if market_raw else []

    return render_template_string(
        INDEX_HTML,
        top_coins=top_coins,
        market_data=market_data,
        wallet=WALLET_ADDRESS,
    )


@app.route("/api/price/<coin_id>")
def api_price(coin_id):
    """API: get coin price"""
    data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin_id in data:
        return jsonify({"coin": coin_id, "data": data[coin_id], "source": "coingecko"})
    return jsonify({"error": "Coin not found"}), 404


@app.route("/api/trending")
def api_trending():
    """API: get trending coins"""
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
    """API: get gas prices across chains with real-time RPC estimates"""
    chains = {
        "ethereum": {"rpc": "https://ethereum-rpc.publicnode.com", "method": "eth_gasPrice"},
        "polygon": {"rpc": "https://polygon-rpc.com", "method": "eth_gasPrice"},
        "arbitrum": {"rpc": "https://arb1.arbitrum.io/rpc", "method": "eth_gasPrice"},
        "base": {"rpc": "https://mainnet.base.org", "method": "eth_gasPrice"},
    }
    results = {}
    for name, cfg in chains.items():
        try:
            r = requests.post(cfg["rpc"], json={"jsonrpc":"2.0","method":cfg["method"],"params":[],"id":1}, timeout=8)
            data = r.json()
            if "result" in data:
                gwei = int(data["result"], 16) / 1e9
                results[name] = {"gas_gwei": round(gwei, 1)}
        except:
            results[name] = {"error": "unavailable"}
    return jsonify(results)


@app.route("/api/health")
def api_health():
    """Health check"""
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "wallet": WALLET_ADDRESS,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/wallet")
def api_wallet():
    """API: check our wallet balance across chains"""
    chains = {
        "ethereum": {"rpc": "https://ethereum-rpc.publicnode.com"},
        "polygon": {"rpc": "https://polygon-rpc.com"},
        "arbitrum": {"rpc": "https://arb1.arbitrum.io/rpc"},
        "base": {"rpc": "https://mainnet.base.org"},
    }
    results = {}
    for name, cfg in chains.items():
        try:
            r = requests.post(cfg["rpc"], json={
                "jsonrpc":"2.0","method":"eth_getBalance",
                "params":[WALLET_ADDRESS, "latest"],"id":1
            }, timeout=8)
            data = r.json()
            if "result" in data:
                bal = int(data["result"], 16) / 1e18
                results[name] = {"balance": bal}
        except:
            results[name] = {"balance": None}
    return jsonify({"wallet": WALLET_ADDRESS, "balances": results})


@app.route("/docs")
def docs():
    """API documentation"""
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
        h1 { color: var(--accent); margin-bottom: 8px; font-size: 28px; }
        h2 { color: var(--accent); margin: 24px 0 12px; font-size: 18px; }
        p { color: var(--muted); margin-bottom: 16px; }
        .endpoint { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; }
        .method { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; margin-right: 8px; }
        .get { background: #22c55e; color: #000; }
        .url { font-family: monospace; font-size: 14px; color: var(--accent); }
        .desc { color: var(--muted); font-size: 13px; margin-top: 4px; }
        pre { background: #0a0b0e; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; margin-top: 8px; }
        a { color: var(--accent); }
        .rate { background: #1e2030; padding: 12px; border-radius: 8px; margin: 16px 0; }
        .rate strong { color: var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" style="color: var(--muted); font-size: 14px;">← Back to Dashboard</a>
        <h1>Crypto Empire API</h1>
        <p>Free public API for crypto market data. No authentication required for basic endpoints.</p>
        
        <div class="rate">
            <strong>🆓 Free Tier:</strong> 100 requests/day · 
            <strong>💎 Premium:</strong> 10,000 requests/day (send <code style="color: var(--accent);">0.005 ETH</code> to wallet with your API key request)
        </div>

        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <span class="method get">GET</span><span class="url">/api/price/&lt;coin_id&gt;</span>
            <div class="desc">Get current price for any CoinGecko-listed coin.</div>
            <pre>curl https://crypto-empire-ten.vercel.app/api/price/bitcoin</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span><span class="url">/api/trending</span>
            <div class="desc">Get currently trending coins on CoinGecko.</div>
            <pre>curl https://crypto-empire-ten.vercel.app/api/trending</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span><span class="url">/api/gas</span>
            <div class="desc">Get real-time gas prices for Ethereum, Polygon, Arbitrum, and Base.</div>
            <pre>curl https://crypto-empire-ten.vercel.app/api/gas</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span><span class="url">/api/wallet</span>
            <div class="desc">Get wallet balances across all supported chains.</div>
            <pre>curl https://crypto-empire-ten.vercel.app/api/wallet</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span><span class="url">/api/health</span>
            <div class="desc">Health check endpoint.</div>
            <pre>curl https://crypto-empire-ten.vercel.app/api/health</pre>
        </div>

        <h2>Support</h2>
        <p>If you find this API useful, consider supporting development:</p>
        <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px;font-family:monospace;font-size:13px;color:var(--accent);word-break:break-all;">
            {{ wallet }}
        </div>
        <p style="margin-top:16px;"><a href="https://github.com/ghassan-gaidi/crypto-empire">GitHub</a></p>
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
    print(f"📊 Dashboard: http://localhost:{port}")
    print(f"🔗 API: http://localhost:{port}/api/health")
    app.run(host="0.0.0.0", port=port, debug=debug)
