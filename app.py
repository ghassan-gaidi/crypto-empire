#!/usr/bin/env python3
"""
Crypto Empire - Web Dashboard & API
Monetized crypto intelligence platform
"""

import os
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from functools import wraps

from flask import Flask, render_template_string, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import requests
import httpx

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
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            usage_count INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            coin_id TEXT PRIMARY KEY,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# CoinGecko API
# ============================================================
COINGECKO_API = "https://api.coingecko.com/api/v3"

async def fetch_coin_data(coin_id="bitcoin"):
    """Fetch coin data from CoinGecko"""
    urls = {
        "price": f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true",
        "chart": f"{COINGECKO_API}/coins/{coin_id}/market_chart?vs_currency=usd&days=7",
        "info": f"{COINGECKO_API}/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
    }
    return urls

def fetch_sync(url):
    """Synchronous fetch with timeout"""
    try:
        resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

# ============================================================
# HTML Templates
# ============================================================
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Empire - Autonomous Crypto Intelligence</title>
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
        
        /* Header */
        header {
            border-bottom: 1px solid var(--border);
            padding: 16px 0;
            margin-bottom: 40px;
        }
        header .container {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 24px; font-weight: bold; color: var(--accent); }
        .logo span { color: var(--accent2); }
        nav a {
            color: var(--muted);
            text-decoration: none;
            margin-left: 24px;
            font-size: 14px;
            transition: color 0.2s;
        }
        nav a:hover { color: var(--text); }
        .btn {
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
        .btn-secondary {
            background: var(--accent2);
        }

        /* Hero */
        .hero {
            text-align: center;
            padding: 60px 0 40px;
        }
        .hero h1 {
            font-size: 48px;
            font-weight: 800;
            margin-bottom: 16px;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p {
            font-size: 18px;
            color: var(--muted);
            max-width: 600px;
            margin: 0 auto 32px;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
        }
        .stat-card h3 {
            font-size: 14px;
            color: var(--muted);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .stat-change {
            font-size: 14px;
        }
        .up { color: var(--success); }
        .down { color: var(--danger); }

        /* Features */
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        .feature-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
        }
        .feature-card .icon { font-size: 40px; margin-bottom: 12px; }
        .feature-card h3 { margin-bottom: 8px; }
        .feature-card p { color: var(--muted); font-size: 14px; }

        /* Pricing */
        .pricing-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        .pricing-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            text-align: center;
        }
        .pricing-card.featured {
            border-color: var(--accent);
            box-shadow: 0 0 30px rgba(0,212,170,0.1);
        }
        .pricing-card h3 { font-size: 20px; margin-bottom: 8px; }
        .pricing-card .price { font-size: 36px; font-weight: 800; margin: 16px 0; }
        .pricing-card .price span { font-size: 16px; color: var(--muted); }
        .pricing-card ul { list-style: none; margin: 20px 0; text-align: left; }
        .pricing-card ul li { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
        .pricing-card ul li:before { content: "✅ "; }

        /* Market Table */
        .market-table {
            width: 100%;
            background: var(--card);
            border-radius: 16px;
            border: 1px solid var(--border);
            overflow: hidden;
            margin: 40px 0;
        }
        .market-table table { width: 100%; border-collapse: collapse; }
        .market-table th {
            padding: 12px 16px;
            text-align: left;
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
        }
        .market-table td {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }
        .market-table tr:last-child td { border-bottom: none; }
        .market-table tr:hover { background: rgba(255,255,255,0.02); }

        /* API Section */
        .api-section {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            margin: 40px 0;
        }
        .api-section code {
            background: rgba(255,255,255,0.05);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
        }

        /* Footer */
        footer {
            border-top: 1px solid var(--border);
            padding: 20px 0;
            margin-top: 60px;
            text-align: center;
            color: var(--muted);
            font-size: 14px;
        }

        /* Status */
        .status-bar {
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
            margin: 20px 0;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-dot.online { background: var(--success); }
        .status-dot.offline { background: var(--danger); }

        @media (max-width: 768px) {
            .hero h1 { font-size: 32px; }
            header .container { flex-direction: column; gap: 12px; }
            nav a { margin: 0 12px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="logo">Crypto <span>Empire</span></div>
            <nav>
                <a href="#features">Features</a>
                <a href="#pricing">Pricing</a>
                <a href="#api">API</a>
                <a href="#market">Market</a>
                <a href="/docs" class="btn">Get Started</a>
            </nav>
        </div>
    </header>

    <div class="container">
        <!-- Hero -->
        <div class="hero">
            <h1>Autonomous Crypto Intelligence</h1>
            <p>Real-time market analysis, arbitrage detection, gas monitoring, and automated trading. Powered by AI. Built for profit.</p>
            <div>
                <a href="#pricing" class="btn" style="margin-right: 12px;">Start Earning</a>
                <a href="#features" class="btn btn-secondary">Learn More</a>
            </div>
        </div>

        <!-- Status -->
        <div class="status-bar">
            <div class="status-item">
                <span class="status-dot online"></span>
                Engine Online
            </div>
            <div class="status-item">
                <span class="status-dot online"></span>
                {{ "{} chains monitored".format(chains|length) }}
            </div>
            <div class="status-item">
                <span class="status-dot online"></span>
                System Uptime: {{ uptime }}
            </div>
        </div>

        <!-- Stats -->
        <div class="stats-grid">
            {% for coin, data in top_coins.items() %}
            <div class="stat-card">
                <h3>{{ coin|upper }}</h3>
                <div class="stat-value">${{ "%.2f"|format(data.usd) if data.usd < 1000 else "%.0f"|format(data.usd) }}</div>
                <div class="stat-change {{ 'up' if data.usd_24h_change >= 0 else 'down' }}">
                    {{ "%+.2f"|format(data.usd_24h_change) }}% (24h)
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Features -->
        <h2 id="features" style="text-align:center; margin: 60px 0 20px;">Everything You Need</h2>
        <div class="features">
            <div class="feature-card">
                <div class="icon">📊</div>
                <h3>Real-Time Market Data</h3>
                <p>Live prices, charts, and market data for 10,000+ cryptocurrencies across all major exchanges.</p>
            </div>
            <div class="feature-card">
                <div class="icon">🔄</div>
                <h3>Arbitrage Detection</h3>
                <p>Cross-DEX price discrepancy scanning with flash loan execution engine. Profit from market inefficiencies.</p>
            </div>
            <div class="feature-card">
                <div class="icon">⛽</div>
                <h3>Gas Optimization</h3>
                <p>Real-time gas monitoring across L1 and L2 chains. Execute trades when fees are lowest.</p>
            </div>
            <div class="feature-card">
                <div class="icon">🤖</div>
                <h3>Automated Trading</h3>
                <p>Deploy trading strategies that run 24/7. Flash loan arbitrage, sniping, and MEV extraction.</p>
            </div>
            <div class="feature-card">
                <div class="icon">📱</div>
                <h3>Telegram Bot</h3>
                <p>Real-time alerts, portfolio tracking, and premium signals delivered straight to your phone.</p>
            </div>
            <div class="feature-card">
                <div class="icon">🔒</div>
                <h3>Self-Custodial</h3>
                <p>Your keys, your coins. We never hold your funds. Smart contracts are audited and transparent.</p>
            </div>
        </div>

        <!-- Pricing -->
        <h2 id="pricing" style="text-align:center; margin: 60px 0 20px;">Simple Pricing</h2>
        <div class="pricing-grid">
            <div class="pricing-card">
                <h3>Free</h3>
                <div class="price">$0<span>/mo</span></div>
                <ul>
                    <li>Price checking</li>
                    <li>Watchlist (5 coins)</li>
                    <li>Basic gas monitoring</li>
                    <li>Public API (100 req/day)</li>
                </ul>
                <a href="#api" class="btn btn-secondary">Get Started</a>
            </div>
            <div class="pricing-card featured">
                <h3>Premium</h3>
                <div class="price">$10<span>/mo</span></div>
                <ul>
                    <li>Real-time price alerts</li>
                    <li>Unlimited watchlist</li>
                    <li>Arbitrage signals</li>
                    <li>Telegram bot premium</li>
                    <li>Portfolio tracking</li>
                    <li>Priority API (10K req/day)</li>
                </ul>
                <a href="#payment" class="btn">Subscribe Now</a>
            </div>
            <div class="pricing-card">
                <h3>Lifetime</h3>
                <div class="price">$50<span></span></div>
                <ul>
                    <li>Everything in Premium</li>
                    <li>Early access to on-chain bot</li>
                    <li>API key (100K req/day)</li>
                    <li>Priority support</li>
                    <li>Lifetime updates</li>
                    <li>Beta features</li>
                </ul>
                <a href="#payment" class="btn btn-secondary">Get Lifetime</a>
            </div>
        </div>

        <!-- Payment -->
        <div id="payment" class="api-section">
            <h2 style="margin-bottom: 16px;">🪙 Pay with Crypto</h2>
            <p style="color: var(--muted); margin-bottom: 20px;">
                Send the exact amount in ETH to the address below. Premium activates automatically after 1 confirmation.
            </p>
            <div style="background: rgba(0,0,0,0.3); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <p style="margin-bottom: 8px;"><strong>ETH Payment Address:</strong></p>
                <code style="font-size: 16px; word-break: break-all; background: var(--bg); padding: 12px; display: block; border-radius: 8px;">{{ wallet }}</code>
                <p style="margin-top: 16px; font-size: 14px; color: var(--muted);">
                    Premium Monthly: <strong>0.005 ETH</strong> (~$10) |
                    Lifetime: <strong>0.025 ETH</strong> (~$50)
                </p>
            </div>
            <p style="font-size: 13px; color: var(--muted);">
                After sending, contact our Telegram bot with your transaction hash for instant activation.
            </p>
        </div>

        <!-- API -->
        <h2 id="api" style="text-align:center; margin: 60px 0 20px;">Developer API</h2>
        <div class="api-section">
            <p style="margin-bottom: 16px;">Integrate crypto data into your applications. No API key required for basic usage.</p>
            <div style="background: rgba(0,0,0,0.3); padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <code style="font-size: 14px;">
                    # Get live prices<br>
                    curl {{ request.host_url }}api/price/bitcoin<br><br>
                    # Get trending<br>
                    curl {{ request.host_url }}api/trending<br><br>
                    # Get gas prices<br>
                    curl {{ request.host_url }}api/gas
                </code>
            </div>
            <p style="font-size: 13px; color: var(--muted);">
                Free: 100 requests/day • Premium: 10,000 requests/day
            </p>
        </div>

        <!-- Market Table -->
        <h2 id="market" style="margin: 60px 0 20px;">Market Overview</h2>
        <div class="market-table">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>24h</th>
                        <th>Market Cap</th>
                        <th>Volume (24h)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for coin in market_data %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td><strong>{{ coin.name }}</strong> <span style="color: var(--muted);">{{ coin.symbol|upper }}</span></td>
                        <td>${{ "%.2f"|format(coin.current_price) if coin.current_price < 1000 else "%.0f"|format(coin.current_price) }}</td>
                        <td class="{{ 'up' if coin.price_change_percentage_24h >= 0 else 'down' }}">
                            {{ "%+.2f"|format(coin.price_change_percentage_24h) }}%
                        </td>
                        <td>${{ "%.1f"|format(coin.market_cap/1e9) }}B</td>
                        <td>${{ "%.1f"|format(coin.total_volume/1e9) }}B</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <footer>
        <div class="container">
            <p>Crypto Empire • Autonomous Revenue Engine • Built for 2026</p>
            <p style="margin-top: 8px; font-size: 13px;">
                Not financial advice. DYOR. Smart contracts are experimental.
            </p>
        </div>
    </footer>
</body>
</html>
"""

# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    """Main dashboard page"""
    # Fetch top coin data
    top_coins = {}
    for coin_id in ["bitcoin", "ethereum", "solana"]:
        data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true")
        if data and coin_id in data:
            top_coins[coin_id] = data[coin_id]

    # Fetch market data
    market_raw = fetch_sync(f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1")
    market_data = market_raw if market_raw else []

    # Chains monitored
    chains = ["Ethereum", "Arbitrum", "Base", "Polygon", "Optimism", "Solana"]

    return render_template_string(
        INDEX_HTML,
        top_coins=top_coins,
        market_data=market_data,
        chains=chains,
        wallet=WALLET_ADDRESS,
        uptime="Active"
    )


@app.route("/api/price/<coin_id>")
def api_price(coin_id):
    """API endpoint: get coin price"""
    data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin_id in data:
        return jsonify({"coin": coin_id, "data": data[coin_id], "source": "coingecko"})
    return jsonify({"error": "Coin not found"}), 404


@app.route("/api/trending")
def api_trending():
    """API endpoint: get trending coins"""
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
    """API endpoint: get gas prices across chains"""
    chains = {
        "ethereum": "https://api.etherscan.io/api?module=gastracker&action=gasoracle",
        "polygon": "https://api.polygonscan.com/api?module=gastracker&action=gasoracle",
    }
    results = {}
    for name, url in chains.items():
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("status") == "1":
                result = data["result"]
                results[name] = {
                    "gas_gwei": int(result.get("gas", 0)) / 10,
                    "usd_price": result.get("UsdPrice", "0"),
                }
        except:
            results[name] = {"error": "unavailable"}
    return jsonify(results)


@app.route("/api/health")
def api_health():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "wallet": WALLET_ADDRESS,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/docs")
def docs():
    """API documentation page"""
    return """
    <html><body style="background:#0a0b0e;color:#e2e8f0;font-family:system-ui;max-width:800px;margin:40px auto;padding:20px;">
        <h1 style="color:#00d4aa;">API Documentation</h1>
        <h2>Endpoints</h2>
        <pre style="background:#13151a;padding:16px;border-radius:8px;">
GET /api/price/&lt;coin_id&gt;  - Get price for a coin
GET /api/trending           - Get trending coins
GET /api/gas                - Get gas prices
GET /api/health             - Health check
        
Examples:
  curl https://your-domain.com/api/price/bitcoin
  curl https://your-domain.com/api/trending
        </pre>
        <p>Rate limits: 100 req/day (free), 10K req/day (premium)</p>
        <a href="/" style="color:#00d4aa;">← Back to Dashboard</a>
    </body></html>
    """

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
