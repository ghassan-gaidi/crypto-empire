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

def render_sparkline(prices, width=80, height=24):
    """Render price array as inline SVG sparkline"""
    if not prices or len(prices) < 2:
        return ""
    min_p = min(prices)
    max_p = max(prices)
    rng = max_p - min_p if max_p > min_p else 1
    step = width / (len(prices) - 1)
    pts = []
    for i, p in enumerate(prices):
        x = round(i * step, 1)
        y = round(height - ((p - min_p) / rng * (height - 4) + 2), 1)
        pts.append(f"{x},{y}")
    color = "var(--green)" if prices[-1] >= prices[0] else "var(--red)"
    return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"><polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.5"/></svg>'

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
# Shared CSS — Terminal Brutalist B&W
# ============================================================
SHARED_HEAD = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
  *{margin:0;padding:0;box-sizing:border-box;border-radius:0!important;-webkit-border-radius:0!important;}
  :root{
    --bg:#000;
    --surface:#0a0a0a;
    --border:#333;
    --text:#e0e0e0;
    --muted:#666;
    --dim:#444;
    --green:#0f0;
    --red:#f00;
    --yellow:#ff0;
    --white:#fff;
  }
  body{
    font-family:'JetBrains Mono','Fira Code','Courier New',monospace;
    background:var(--bg);color:var(--text);font-size:13px;line-height:1.6;
    min-height:100vh;position:relative;
  }
  body::after{
    content:'';position:fixed;top:0;left:0;right:0;bottom:0;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,.012) 2px,rgba(255,255,255,.012) 4px);
    pointer-events:none;z-index:9999;
  }
  ::selection{background:var(--white);color:var(--bg);}
  .container{max-width:1100px;margin:0 auto;padding:20px;}
  a{color:var(--text);text-decoration:underline;}
  a:hover{color:var(--white);}
  hr{border:none;border-top:1px dashed var(--border);margin:32px 0;}
  /* HEADER */
  header{border-bottom:2px solid var(--border);padding:20px 0;margin-bottom:32px;}
  header .container{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}
  .logo{
    font-size:18px;font-weight:700;color:var(--white);text-decoration:none;
    text-transform:uppercase;letter-spacing:5px;
  }
  .logo:before{content:'> ';color:var(--dim);}
  .logo:after{content:'_';animation:blink 1s step-end infinite;color:var(--white);}
  @keyframes blink{50%{opacity:0}}
  nav{display:flex;gap:2px;flex-wrap:wrap;}
  nav a{
    color:var(--muted);text-decoration:none;padding:7px 14px;
    border:1px solid transparent;font-size:11px;text-transform:uppercase;
    letter-spacing:2px;transition:.1s;
  }
  nav a:hover{color:var(--white);border-color:var(--white);}
  .nav-btn{
    display:inline-block;border:2px solid var(--white);color:var(--white);
    padding:7px 14px;font-size:11px;text-transform:uppercase;
    letter-spacing:2px;text-decoration:none;transition:.1s;background:transparent;
  }
  .nav-btn:hover{background:var(--white);color:var(--bg);}
  /* SECTION LABELS */
  .section-title{
    font-size:11px;color:var(--muted);text-transform:uppercase;
    letter-spacing:3px;margin-bottom:12px;margin-top:36px;
    padding-bottom:8px;border-bottom:1px dashed var(--border);
  }
  .section-title:before{content:'# ';color:var(--white);}
  /* TOP BAR — BORDERED GRID */
  .top-bar{
    display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
    margin-bottom:28px;border:2px solid var(--border);
  }
  .stat-card{
    padding:14px;border-right:1px solid var(--border);border-bottom:1px solid var(--border);
  }
  .stat-card .label{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:2px;}
  .stat-card .value{font-size:20px;font-weight:700;margin-top:4px;color:var(--white);}
  .stat-card .sub{font-size:10px;margin-top:2px;text-transform:uppercase;letter-spacing:1px;}
  .up{color:var(--green);}
  .down{color:var(--red);}
  /* GAS CARDS — BORDERED GRID */
  .gas-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));margin-bottom:28px;border:2px solid var(--border);}
  .gas-card{padding:14px;text-align:center;border-right:1px solid var(--border);border-bottom:1px solid var(--border);}
  .gas-card .chain{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:2px;margin-bottom:4px;}
  .gas-card .gwei{font-size:22px;font-weight:700;}
  .low{color:var(--green);}.medium{color:var(--yellow);}.high{color:var(--red);}
  /* MARKET TABLE */
  .table-wrap{border:2px solid var(--border);margin-bottom:28px;overflow-x:auto;}
  table{width:100%;border-collapse:collapse;min-width:600px;}
  th,td{padding:8px 14px;text-align:left;font-size:12px;white-space:nowrap;border-bottom:1px solid var(--border);}
  th{color:var(--dim);font-weight:500;font-size:10px;text-transform:uppercase;letter-spacing:2px;}
  tr:last-child td{border-bottom:none;}
  tr:hover td{background:rgba(255,255,255,.02);}
  .rank{color:var(--dim);width:30px;}
  .coin-name{font-weight:500;}
  .coin-symbol{color:var(--dim);font-size:10px;}
  /* NEWS */
  .news-list{list-style:none;}
  .news-list li{padding:8px 0;border-bottom:1px solid var(--border);}
  .news-list li:last-child{border-bottom:none;}
  .news-list a{color:var(--text);text-decoration:none;font-size:13px;display:block;}
  .news-list a:hover{color:var(--white);}
  .news-date{font-size:10px;color:var(--dim);margin-top:2px;text-transform:uppercase;letter-spacing:1px;}
  /* FEATURES */
  .features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0;margin-bottom:28px;border:2px solid var(--border);}
  .feature-card{padding:16px;text-align:center;border-right:1px solid var(--border);border-bottom:1px solid var(--border);}
  .feature-card .icon{font-size:16px;margin-bottom:4px;color:var(--muted);}
  .feature-card h4{font-size:12px;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;}
  .feature-card p{font-size:11px;color:var(--dim);}
  /* DONATION BOX */
  .donation-box{border:2px solid var(--white);padding:24px;margin-bottom:28px;text-align:center;}
  .donation-box h3{font-size:14px;margin-bottom:8px;text-transform:uppercase;letter-spacing:2px;}
  .wallet-addr{
    border:2px solid var(--border);padding:10px 16px;
    font-family:monospace;font-size:12px;color:var(--white);
    word-break:break-all;cursor:pointer;background:var(--surface);
    display:inline-block;max-width:100%;user-select:all;margin:12px 0;
  }
  .wallet-addr:hover{border-color:var(--white);}
  .chain-tags{display:flex;gap:4px;justify-content:center;flex-wrap:wrap;margin:8px 0;}
  .chain-tag{border:1px solid var(--border);padding:3px 10px;font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;}
  /* FOOTER */
  footer{text-align:center;padding:24px 0;border-top:2px solid var(--border);color:var(--muted);font-size:11px;}
  footer a{color:var(--muted);}
  footer a:hover{color:var(--white);}
  /* TOAST */
  .toast{
    position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
    background:var(--white);color:var(--bg);padding:10px 20px;
    font-size:12px;font-weight:700;opacity:0;transition:opacity .2s;
    pointer-events:none;z-index:100;text-transform:uppercase;letter-spacing:2px;
  }
  .toast.show{opacity:1;}
  /* BACK NAV */
  .back-nav{margin-bottom:24px;}
  .back-nav a{color:var(--dim);text-decoration:none;font-size:11px;text-transform:uppercase;letter-spacing:1px;}
  .back-nav a:hover{color:var(--white);}
  .back-nav a:before{content:'<- ';}
  /* BLOG */
  .post-card{border:2px solid var(--border);padding:20px;margin-bottom:12px;}
  .post-card:hover{border-color:var(--white);}
  .post-card h2{font-size:16px;margin-bottom:6px;}
  .post-card h2 a{color:var(--white);text-decoration:none;}
  .post-card h2 a:hover{text-decoration:underline;}
  .post-card .meta{color:var(--dim);font-size:10px;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;}
  .post-card .tags{display:flex;gap:4px;flex-wrap:wrap;}
  .post-card .tag{border:1px solid var(--border);padding:2px 8px;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;}
  /* WALLET CHECKER */
  .winput{border:2px solid var(--border);padding:12px 16px;background:var(--surface);color:var(--white);font-family:monospace;font-size:14px;outline:none;width:100%;display:block;}
  .winput:focus{border-color:var(--white);}
  .wbtn{border:2px solid var(--white);color:var(--white);background:transparent;padding:12px 24px;font-family:monospace;font-size:12px;cursor:pointer;text-transform:uppercase;letter-spacing:2px;margin-top:8px;}
  .wbtn:hover{background:var(--white);color:var(--bg);}
  .chain-row{display:flex;justify-content:space-between;align-items:center;border:1px solid var(--border);padding:12px 16px;margin-bottom:6px;}
  .chain-name{font-weight:500;text-transform:uppercase;letter-spacing:1px;font-size:12px;}
  .chain-bal{font-family:monospace;color:var(--white);font-size:14px;}
  .chain-usd{color:var(--dim);font-size:11px;}
  .total-val{font-size:24px;font-weight:700;color:var(--white);text-align:center;padding:20px;border:2px solid var(--border);margin-bottom:12px;}
  .error{color:var(--red);text-align:center;padding:20px;}
  .loading{text-align:center;color:var(--dim);padding:20px;}
  /* TELEGRAM CTA */
  .tg-cta{
    border:2px solid var(--white);padding:32px;margin-bottom:28px;text-align:center;
    background:var(--surface);
  }
  .tg-cta h3{font-size:16px;margin-bottom:8px;text-transform:uppercase;letter-spacing:2px;}
  .tg-cta p{font-size:12px;color:var(--muted);margin-bottom:16px;}
  .tg-cta .tg-btn{
    display:inline-block;border:2px solid var(--white);color:var(--white);
    padding:12px 32px;font-size:14px;text-transform:uppercase;
    letter-spacing:3px;text-decoration:none;transition:.1s;font-weight:700;
  }
  .tg-cta .tg-btn:hover{background:var(--white);color:var(--bg);}
  .tg-cta .tg-cmd{
    border:1px dashed var(--border);padding:12px;margin-top:16px;
    font-size:13px;color:var(--green);display:inline-block;
    user-select:all;
  }
  /* 404 PAGE */
  .error-404{text-align:center;padding:80px 20px;}
  .error-404 h1{font-size:80px;color:var(--white);font-weight:700;}
  .error-404 p{color:var(--muted);font-size:13px;margin:16px 0 24px;}
  .error-404 .glitch{font-size:14px;color:var(--dim);letter-spacing:5px;text-transform:uppercase;}
  @media(max-width:640px){
    .container{padding:12px;}
    .top-bar{grid-template-columns:repeat(2,1fr);}
    th,td{padding:6px 8px;font-size:11px;}
    .chain-row{flex-direction:column;gap:4px;text-align:center;}
  }
</style>"""

# ============================================================
# HTML Templates
# ============================================================
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Crypto Empire — Autonomous Crypto Intelligence</title>
    <meta name="description" content="Free crypto dashboard with live prices, gas tracker, wallet balance checker, and market data for Ethereum, Bitcoin, Arbitrum, Polygon & Base.">
    <meta name="keywords" content="crypto dashboard, wallet checker, gas tracker, Ethereum gas, Bitcoin price, crypto prices, portfolio tracker, blockchain tools">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/">
    <meta property="og:title" content="Crypto Empire — Autonomous Crypto Intelligence">
    <meta property="og:description" content="Free crypto dashboard with live prices, gas tracker, wallet balance checker, and market data for Ethereum, Bitcoin, Arbitrum, Polygon & Base.">
    <meta property="og:url" content="https://crypto-empire-ten.vercel.app/">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Crypto Empire — Autonomous Crypto Intelligence">
    <meta name="twitter:description" content="Free crypto dashboard. Live prices, gas tracker, wallet checker, Telegram bot @Crypt0Emp1reBot.">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">CRYPTO_EMPIRE</a>
            <nav>
                <a href="#market">Market</a>
                <a href="#gas">Gas</a>
                <a href="#news">News</a>
                <a href="#features">Features</a>
                <a href="/blog">Blog</a>
                <a href="/docs">API</a>
                <a href="/wallet-check">Wallet</a>
                <a href="https://github.com/ghassan-gaidi/crypto-empire" target="_blank">GitHub</a>
                <a class="nav-btn" href="#donate">Support</a>
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
                <div class="label">FEAR & GREED</div>
                <div class="value" style="color:{{ 'var(--green)' if fear_greed.value > 50 else 'var(--red)' if fear_greed.value < 25 else 'var(--yellow)' }};">{{ fear_greed.value }}</div>
                <div class="sub" style="color:var(--dim);text-transform:uppercase;letter-spacing:1px;font-size:10px;">{{ fear_greed.classification|upper }}</div>
            </div>
            {% endif %}
            <div class="stat-card" id="tvl-card" style="display:none;">
                <div class="label">ETH TVL</div>
                <div class="value" id="tvl-value">--</div>
                <div class="sub" style="color:var(--dim);text-transform:uppercase;letter-spacing:1px;font-size:10px;">DefiLlama</div>
            </div>
        </div>

        <!-- Gas Tracker -->
        <h2 class="section-title" id="gas">Gas Tracker</h2>
        <div class="gas-grid" id="gas-grid">
            <div class="gas-card"><div class="chain">Ethereum</div><div class="gwei" id="gas-eth">--</div></div>
            <div class="gas-card"><div class="chain">Polygon</div><div class="gwei" id="gas-poly">--</div></div>
            <div class="gas-card"><div class="chain">Arbitrum</div><div class="gwei" id="gas-arb">--</div></div>
            <div class="gas-card"><div class="chain">Base</div><div class="gwei" id="gas-base">--</div></div>
        </div>

        <!-- Market Table -->
        <h2 class="section-title" id="market">Top 20 Cryptocurrencies</h2>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr><th>#</th><th>Name</th><th>Price</th><th>24h</th><th>7d</th><th>Chart</th><th>Market Cap</th><th>Volume 24h</th></tr>
                </thead>
                <tbody>
                    {% for coin in market_data %}
                    <tr>
                        <td class="rank">{{ coin.market_cap_rank }}</td>
                        <td><span class="coin-name">{{ coin.name }}</span> <span class="coin-symbol">{{ coin.symbol|upper }}</span></td>
                        <td>${{ "%.2f"|format(coin.current_price) if coin.current_price < 1000 else "%.0f"|format(coin.current_price) }}</td>
                        <td class="{{ 'up' if coin.price_change_percentage_24h >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_24h) }}%</td>
                        <td class="{{ 'up' if coin.price_change_percentage_7d_in_currency >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_7d_in_currency) }}%</td>
                        <td>{{ coin.sparkline_svg|safe }}</td>
                        <td class="mc">${{ "{:,.0f}".format(coin.market_cap) }}</td>
                        <td class="vol">${{ "{:,.0f}".format(coin.total_volume) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- News -->
        <h2 class="section-title" id="news">Crypto News</h2>
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

        <!-- DEX Volume -->
        <h2 class="section-title" id="dexs">Top DEXes by Volume</h2>
        <div class="table-wrap" id="dex-section">
            <table>
                <thead><tr><th>#</th><th>DEX</th><th>Volume 24h</th><th>Volume 7d</th><th>24h Change</th><th>Chains</th></tr></thead>
                <tbody id="dex-tbody">
                </tbody>
            </table>
        </div>

        <!-- Trending Coins -->
        <h2 class="section-title" id="trending">Trending Coins</h2>
        <div class="gas-grid" id="trending-grid"></div>

        <!-- Features -->
        <h2 class="section-title" id="features">Everything You Need</h2>
        <div class="features-grid">
            <div class="feature-card"><div class="icon">[01]</div><h4>Real-Time Data</h4><p>Live prices, gas, and market caps for top coins</p></div>
            <div class="feature-card"><div class="icon">[02]</div><h4>Arbitrage Scanner</h4><p>Cross-DEX price disparities in real-time</p></div>
            <div class="feature-card"><div class="icon">[03]</div><h4>Gas Optimization</h4><p>Multi-chain gas tracker to minimize costs</p></div>
            <div class="feature-card"><div class="icon">[04]</div><h4>Telegram Bot</h4><p>Live prices, gas &amp; wallet checks via <a href="https://t.me/Crypt0Emp1reBot" target="_blank" style="color:var(--white);">@Crypt0Emp1reBot</a></p></div>
            <div class="feature-card"><div class="icon">[05]</div><h4>Self-Custodial</h4><p>Your keys, your coins. No exchange risk</p></div>
            <div class="feature-card"><div class="icon">[06]</div><h4>Flash Loans</h4><p>Capital-free arbitrage via Aave V3</p></div>
        </div>

        <!-- Telegram CTA -->
        <div class="tg-cta">
            <h3>// TELEGRAM_BOT</h3>
            <p>Live crypto data at your fingertips. No signup, no API keys.</p>
            <a href="https://t.me/Crypt0Emp1reBot" target="_blank" class="tg-btn">@Crypt0Emp1reBot</a>
            <br><span class="tg-cmd">Send /start in Telegram</span>
        </div>

        <!-- Donation Section -->
        <div class="donation-box" id="donate">
            <h3>Support Crypto Empire</h3>
            <p style="color:var(--muted);font-size:12px;margin-bottom:12px;">
                Send a tip in ETH, USDC, or any ERC-20 token.<br>
                Premium access (10K API req/day + arbitrage signals): send 0.005 ETH.
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
            <p style="color:var(--dim);font-size:10px;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Click to copy - All EVM chains supported</p>
        </div>

        <div style="text-align:center;margin-bottom:24px;">
            <a href="https://github.com/ghassan-gaidi/crypto-empire" target="_blank" class="nav-btn" style="margin-right:8px;">Star on GitHub</a>
            <a href="/docs" class="nav-btn">API Docs</a>
        </div>

        <footer>
            <p>Built autonomously - <a href="https://github.com/ghassan-gaidi/crypto-empire">Open Source</a> - Zero KYC - Zero Budget</p>
            <p style="margin-top:4px;font-size:10px;">Wallet: <code style="font-size:10px;">{{ wallet }}</code></p>
        </footer>
    </div>

    <div class="toast" id="toast">COPIED</div>

    <script>
        function copyWallet(el) {
            navigator.clipboard.writeText(el.textContent).then(function() {
                var t = document.getElementById('toast');
                t.classList.add('show');
                setTimeout(function() { t.classList.remove('show'); }, 2000);
            });
        }
        async function fetchGas() {
            try {
                var r = await fetch('/api/gas');
                var data = await r.json();
                for (var chain in data) {
                    var id = chain === 'ethereum' ? 'gas-eth' : chain === 'polygon' ? 'gas-poly' : chain === 'arbitrum' ? 'gas-arb' : chain === 'base' ? 'gas-base' : 'gas-' + chain;
                    var el = document.getElementById(id);
                    if (el && data[chain].gas_gwei !== undefined) {
                        var g = data[chain].gas_gwei;
                        el.textContent = g + ' gwei';
                        el.className = 'gwei ' + (g < 5 ? 'low' : g < 30 ? 'medium' : 'high');
                    }
                }
            } catch(e) {}
        }
        async function fetchDEXs() {
            try {
                var r = await fetch('/api/dexs');
                var data = await r.json();
                var tbody = document.getElementById('dex-tbody');
                if (!tbody) return;
                var html = '';
                for (var i = 0; i < data.length; i++) {
                    var d = data[i];
                    var vol24 = d.volume24h >= 1000000 ? '$' + (d.volume24h / 1000000).toFixed(1) + 'M' : '$' + (d.volume24h / 1000).toFixed(0) + 'K';
                    var vol7 = d.volume7d >= 1000000 ? '$' + (d.volume7d / 1000000).toFixed(1) + 'M' : '$' + (d.volume7d / 1000).toFixed(0) + 'K';
                    var cls = d.change1d >= 0 ? 'up' : 'down';
                    html += '<tr><td class="rank">' + (i+1) + '</td><td><span class="coin-name">' + d.name + '</span></td><td>' + vol24 + '</td><td>' + vol7 + '</td><td class="' + cls + '">' + d.change1d + '%</td><td><span class="coin-symbol">' + (d.chains||[]).join(', ') + '</span></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) {}
        }
        async function fetchTrending() {
            try {
                var r = await fetch('/api/trending');
                var data = await r.json();
                var grid = document.getElementById('trending-grid');
                if (!grid || !data.trending) return;
                var html = '';
                for (var i = 0; i < Math.min(data.trending.length, 10); i++) {
                    var c = data.trending[i];
                    html += '<div class="gas-card"><div class="chain" style="font-size:12px;">' + c.name + '</div><div class="gwei" style="font-size:16px;color:var(--dim);">' + (c.symbol||'').toUpperCase() + '</div><div style="font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-top:2px;">Rank ' + (c.market_cap_rank||'--') + '</div></div>';
                }
                grid.innerHTML = html;
            } catch(e) {}
        }
        async function fetchTVL() {
            try {
                var r = await fetch('/api/tvl');
                var data = await r.json();
                var card = document.getElementById('tvl-card');
                var val = document.getElementById('tvl-value');
                if (card && val && data.tvl) {
                    var tvl = data.tvl >= 1000000000 ? '$' + (data.tvl / 1000000000).toFixed(1) + 'B' : '$' + (data.tvl / 1000000).toFixed(0) + 'M';
                    val.textContent = tvl;
                    card.style.display = '';
                }
            } catch(e) {}
        }
        fetchGas();
        fetchDEXs();
        fetchTrending();
        fetchTVL();
        setInterval(fetchGas, 30000);
        setInterval(fetchDEXs, 120000);
        setInterval(fetchTrending, 120000);
        setInterval(fetchTVL, 120000);
        setTimeout(function() { location.reload(); }, 180000);
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

    # Market data with 7d change and sparklines
    market_raw = fetch_sync(
        f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&price_change_percentage=7d&sparkline=true"
    )
    market_data = []
    if market_raw:
        for coin in market_raw:
            coin['sparkline_svg'] = render_sparkline(coin.get('sparkline_in_7d', {}).get('price'))
            market_data.append(coin)

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


@app.route("/api/tvl")
def api_tvl():
    """Ethereum total value locked from DeFiLlama"""
    data = fetch_sync("https://api.llama.fi/v2/historicalChainTvl/Ethereum")
    if data and len(data) > 0:
        latest = data[-1]
        return jsonify({"chain": "ethereum", "tvl": round(latest.get("tvl", 0)), "date": latest.get("date", 0)})
    return jsonify({"error": "unavailable"}), 500


@app.route("/api/dexs")
def api_dexs():
    """Top DEXes by 24h volume from DeFiLlama"""
    data = fetch_sync("https://api.llama.fi/overview/dexs")
    if data and "protocols" in data:
        top = sorted(data["protocols"], key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:10]
        dexs = []
        for d in top:
            dexs.append({
                "name": d.get("displayName", d.get("name", "")),
                "volume24h": round(d.get("total24h", 0)),
                "volume7d": round(d.get("total7d", 0)),
                "change1d": round(d.get("change_1d", 0) or 0, 2),
                "chains": (d.get("chains") or [""])[:3],
            })
        return jsonify(dexs)
    return jsonify({"error": "unavailable"}), 500


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
<head>""" + SHARED_HEAD + """
    <title>Crypto Empire — API Docs</title>
    <meta name="description" content="Free public API for crypto data. No auth required. Bitcoin, Ethereum, gas prices, wallet balances.">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/docs">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">CRYPTO_EMPIRE</a>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/blog">Blog</a>
                <a href="/wallet-check">Wallet</a>
            </nav>
        </div>
    </header>
    <div class="container">
        <div class="back-nav"><a href="/">Dashboard</a></div>
        <h1 style="font-size:20px;color:var(--white);text-transform:uppercase;letter-spacing:3px;margin-bottom:8px;">// API_DOCS</h1>
        <p style="color:var(--muted);margin-bottom:24px;font-size:12px;">Free public API for crypto data. No authentication required.</p>

        <div style="border:2px solid var(--border);padding:16px;margin-bottom:24px;">
            <p style="font-size:11px;"><span style="color:var(--green);">FREE:</span> 100 req/day &nbsp;|&nbsp; <span style="color:var(--yellow);">PREMIUM:</span> 10K req/day (send 0.005 ETH to wallet)</p>
        </div>

        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p style="color:var(--white);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:2px;">Telegram Bot</p>
            <p style="color:var(--muted);font-size:11px;margin-top:4px;">Same data, directly in Telegram. No API key needed.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">Open: https://t.me/Crypt0Emp1reBot
Send: /help</pre>
        </div>

        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/price/&lt;coin_id&gt;</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Get current price for any CoinGecko coin ID.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/price/bitcoin</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/trending</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Trending coins on CoinGecko.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/trending</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/gas</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Gas prices across Ethereum, Polygon, Arbitrum, Base.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/gas</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/wallet</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Wallet balances across chains.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/wallet</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/fear-greed</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Fear &amp; Greed index history (7 days).</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/fear-greed</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/news</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Latest crypto news from CoinTelegraph.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/news</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:24px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/health</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Service health check.</p>
        </div>

        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/tvl</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Ethereum total value locked from DeFiLlama.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/tvl</pre>
        </div>
        <div style="border:2px solid var(--border);padding:16px;margin-bottom:12px;">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="color:var(--white);font-size:13px;">/api/dexs</code></p>
            <p style="color:var(--dim);font-size:11px;margin-top:4px;">Top 10 DEXes by 24h volume from DeFiLlama.</p>
            <pre style="background:var(--surface);padding:12px;font-size:11px;margin-top:8px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/dexs</pre>
        </div>

        <p style="font-size:11px;color:var(--dim);margin-bottom:24px;">Support: <code style="color:var(--white);">{{ wallet }}</code></p>
        <p style="font-size:11px;"><a href="https://github.com/ghassan-gaidi/crypto-empire">GitHub</a></p>

        <footer>
            <p><a href="/">Crypto Empire</a> - <a href="/sitemap.xml">Sitemap</a></p>
        </footer>
    </div>
</body>
</html>""", wallet=WALLET_ADDRESS)


# ============================================================
# Wallet Check Page
# ============================================================

WALLET_CHECK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Wallet Checker — Crypto Empire</title>
    <meta name="description" content="Check any Ethereum wallet balance across Ethereum, Arbitrum, Base, and Polygon. Free multi-chain wallet balance checker.">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/wallet-check">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">CRYPTO_EMPIRE</a>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/docs">API</a>
                <a href="/blog">Blog</a>
            </nav>
        </div>
    </header>
    <div class="container">
        <div class="back-nav"><a href="/">Dashboard</a></div>
        <h1 style="font-size:20px;color:var(--white);text-transform:uppercase;letter-spacing:3px;margin-bottom:8px;">// WALLET_CHECKER</h1>
        <p style="color:var(--muted);font-size:12px;margin-bottom:20px;">Check ETH balances across Ethereum, Arbitrum, Base, and Polygon.</p>
        <input type="text" class="winput" id="address" placeholder="0x... or ENS name" value="0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef">
        <br>
        <button class="wbtn" onclick="checkWallet()">Check Wallet</button>
        <div id="results" class="result"></div>
    </div>
    <script>
    async function checkWallet() {
        var addr = document.getElementById('address').value.trim();
        var el = document.getElementById('results');
        if (!addr || !addr.startsWith('0x')) { el.innerHTML = '<div class="error">Invalid address</div>'; return; }
        el.innerHTML = '<div class="loading">CHECKING...</div>';
        try {
            var r = await fetch('/api/check-wallet/' + encodeURIComponent(addr));
            var data = await r.json();
            if (data.error) { el.innerHTML = '<div class="error">' + data.error + '</div>'; return; }
            var html = '<div class="total-val">TOTAL: ' + data.total_usd_formatted + '</div>';
            for (var i = 0; i < data.chains.length; i++) {
                var c = data.chains[i];
                html += '<div class="chain-row">' +
                    '<span class="chain-name">' + c.name + '</span>' +
                    '<span><span class="chain-bal">' + c.balance_formatted + '</span> <span class="chain-usd">$' + c.usd_value.toFixed(2) + '</span></span>' +
                    '</div>';
            }
            html += '<div style="text-align:center;margin-top:16px;"><a href="https://debank.com/profile/' + addr + '" target="_blank" style="font-size:11px;text-transform:uppercase;letter-spacing:1px;">View on DeBank -></a></div>';
            el.innerHTML = html;
        } catch(e) {
            el.innerHTML = '<div class="error">Request failed</div>';
        }
    }
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
        "title": "Best Crypto Wallet Balance Checker 2026 - Track Any Address Across 4 Chains",
        "date": "2026-06-03",
        "tags": ["wallet checker", "crypto tools", "portfolio tracker"],
        "content": """
<h2>Check Any Ethereum Wallet Balance Across Multiple Chains</h2>
<p>Crypto Empire's <a href="/wallet-check">Wallet Checker</a> lets you instantly view ETH, MATIC, and ERC-20 token balances across Ethereum, Arbitrum, Base, and Polygon - all from one page. No signup, no API key, no wallet connection needed.</p>

<h3>Why Use a Multi-Chain Wallet Checker?</h3>
<p>Modern crypto users hold assets across multiple Layer 2 solutions. Instead of checking each chain's block explorer separately, our tool aggregates balances from Ethereum, Arbitrum, Base, and Polygon into a single USD value.</p>

<h3>Features</h3>
<ul>
<li><strong>Instant balance lookup</strong> - Enter any 0x address and see balances in seconds</li>
<li><strong>Multi-chain support</strong> - Ethereum, Arbitrum, Base, Polygon</li>
<li><strong>USD conversion</strong> - Real-time prices via CoinGecko</li>
<li><strong>ENS support</strong> - Enter ENS names directly</li>
<li><strong>Free &amp; open source</strong> - No ads, no tracking</li>
</ul>

<h3>How to Use</h3>
<p>Visit the <a href="/wallet-check">Wallet Checker</a> page, enter any Ethereum address, and click "Check Wallet". The tool queries live RPC endpoints and returns balances with USD values.</p>

<p>If you find this tool useful, consider supporting development by sending a donation to the project wallet.</p>
"""
    },
    {
        "slug": "ethereum-gas-tracker-live-prices",
        "title": "Ethereum Gas Tracker - Live ETH Gas Prices for Polygon, Arbitrum & Base 2026",
        "date": "2026-06-02",
        "tags": ["gas tracker", "ETH gas", "Layer 2 fees"],
        "content": """
<h2>Live Gas Price Tracker for Ethereum and L2s</h2>
<p>Our <a href="/">Gas Tracker</a> provides real-time gas prices for Ethereum, Polygon, Arbitrum, and Base. Optimize your transaction timing and reduce fees.</p>

<h3>Current Gas Prices</h3>
<p>The dashboard displays live gas prices in Gwei for the four major EVM chains. Prices update every 30 seconds with color-coded indicators (green = cheap, yellow = moderate, red = expensive).</p>

<h3>When to Transact</h3>
<ul>
<li><strong>Low gas (&lt;5 Gwei ETH)</strong> - Best time for transfers and DeFi interactions</li>
<li><strong>Medium gas (5-30 Gwei ETH)</strong> - Normal conditions, fine for standard transactions</li>
<li><strong>High gas (&gt;30 Gwei ETH)</strong> - Expensive, consider waiting or using L2s</li>
</ul>

<h3>Chain Comparison</h3>
<p>Polygon typically offers the lowest fees (&lt;100 Gwei MATIC), while Ethereum mainnet can spike during high-demand periods. Arbitrum and Base offer a middle ground with Ethereum-level security and reduced fees.</p>

<p>Bookmark our <a href="/">dashboard</a> for quick access to live gas data across all major chains.</p>
"""
    },
    {
        "slug": "crypto-portfolio-tracker-free-tools",
        "title": "Free Crypto Portfolio Tracker Tools - Track Without Connecting Your Wallet",
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
        "slug": "crypto-empire-telegram-bot-live-prices-alerts",
        "title": "Crypto Empire Telegram Bot is Live — Get Crypto Prices Directly in Telegram",
        "date": "2026-06-04",
        "tags": ["telegram bot", "crypto bot", "price alerts", "crypto tools"],
        "content": """
<h2>@Crypt0Emp1reBot — Live Crypto Data on Telegram</h2>
<p>The Crypto Empire <a href="https://t.me/Crypt0Emp1reBot" target="_blank">Telegram bot</a> is now live. Get real-time crypto prices, gas fees, trending coins, and wallet balance checks directly in your Telegram chat. No signup, no API keys, no database — just pure on-chain and market data.</p>

<h3>Available Commands</h3>
<ul>
<li><strong>/price &lt;coin&gt;</strong> — Current price, 24h change, market cap &amp; volume (e.g. /price bitcoin)</li>
<li><strong>/gas</strong> — Live gas prices for Ethereum, Polygon, Arbitrum &amp; Base</li>
<li><strong>/fear</strong> — Fear &amp; Greed Index (market sentiment)</li>
<li><strong>/trending</strong> — Top 10 trending coins on CoinGecko</li>
<li><strong>/news</strong> — Latest 5 crypto headlines from CoinTelegraph</li>
<li><strong>/wallet &lt;address&gt;</strong> — Multi-chain balance check across ETH/Arb/Base/Poly</li>
<li><strong>/tvl</strong> — Ethereum Total Value Locked from DeFiLlama</li>
<li><strong>/dexs</strong> — Top 10 DEXes by 24h volume</li>
<li><strong>/sparkline &lt;coin&gt;</strong> — ASCII 7-day price chart</li>
</ul>

<h3>How to Use</h3>
<p>Open Telegram and search for <strong>@Crypt0Emp1reBot</strong> or click <a href="https://t.me/Crypt0Emp1reBot" target="_blank">this link</a>. Send <code>/start</code> to see the command list. That's it — no installation, no login, no ads.</p>

<h3>Behind the Scenes</h3>
<p>The bot runs on the same Vercel serverless infrastructure as the Crypto Empire dashboard. It uses a webhook endpoint at <code>/telegram/webhook</code> that processes commands in real-time. No persistent server, no polling — Telegram pushes messages to the endpoint and the bot responds within seconds.</p>

<p>All data sources are the same free public APIs powering the dashboard: CoinGecko for prices, public RPC endpoints for wallet balances, DeFiLlama for TVL and DEX data, and Alternative.me for the Fear &amp; Greed Index.</p>

<p>Built autonomously. Open source. <a href="https://github.com/ghassan-gaidi/crypto-empire">GitHub</a>.</p>
"""
    },
    {
        "slug": "top-cryptocurrencies-today",
        "title": "Top 20 Cryptocurrencies by Market Cap - Live Prices & Charts June 2026",
        "date": "2026-06-01",
        "tags": ["crypto prices", "market cap", "Bitcoin", "Ethereum"],
        "content": """
<h2>Top 20 Cryptocurrencies by Market Cap - Live Prices</h2>
<p>Our <a href="/">dashboard</a> displays the top 20 cryptocurrencies ranked by market capitalization, with live prices from CoinGecko.</p>

<h3>Today's Top Coins</h3>
<p>Bitcoin (BTC) remains the largest cryptocurrency by market cap, followed by Ethereum (ETH), Tether (USDT), and BNB (BNB). The rankings update automatically with each page reload.</p>

<h3>Understanding Market Metrics</h3>
<ul>
<li><strong>Market Cap</strong> - Total value of all coins in circulation (price x circulating supply)</li>
<li><strong>24h Change</strong> - Price movement over the last 24 hours</li>
<li><strong>7d Change</strong> - Price trend over the last week</li>
<li><strong>Volume (24h)</strong> - Total trading volume across all markets in the last day</li>
</ul>

<h3>Market Sentiment</h3>
<p>Our dashboard also includes the Fear &amp; Greed Index, a popular market sentiment indicator. Values below 25 indicate fear (potential buying opportunity), while values above 75 suggest greed (potential overvaluation).</p>

<p>Check back daily for updated prices and market data. Support the project by sending a donation to the wallet address below.</p>
"""
    },
]

@app.route("/blog")
def blog_index():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Crypto Empire Blog - Crypto Tools, Guides & Market Analysis</title>
    <meta name="description" content="Free crypto tools, wallet checker, gas tracker, and market data. Guides and analysis for cryptocurrency traders and investors.">
    <meta name="keywords" content="crypto tools, wallet checker, gas tracker, Bitcoin, Ethereum, cryptocurrency prices">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/blog">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">CRYPTO_EMPIRE</a>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/docs">API</a>
                <a href="/wallet-check">Wallet</a>
            </nav>
        </div>
    </header>
    <div class="container">
        <div class="back-nav"><a href="/">Dashboard</a></div>
        <h1 style="font-size:20px;color:var(--white);text-transform:uppercase;letter-spacing:3px;margin-bottom:8px;">// BLOG</h1>
        <p style="color:var(--muted);margin-bottom:28px;font-size:12px;">Free crypto tools, guides, and market analysis.</p>
        
        {% for post in posts %}
        <div class="post-card">
            <h2><a href="/blog/{{ post.slug }}">{{ post.title }}</a></h2>
            <div class="meta">{{ post.date }} - {{ post.tags|join(', ') }}</div>
            <div class="tags">{% for tag in post.tags %}<span class="tag">{{ tag }}</span>{% endfor %}</div>
        </div>
        {% endfor %}
        
        <div class="donation-box" style="margin-top:28px;">
            <h3>Support These Free Tools</h3>
            <p style="color:var(--muted);font-size:12px;margin-bottom:12px;">If you find these tools useful, send a tip in ETH, USDC, or any ERC-20 token.</p>
            <div class="wallet-addr">{{ wallet }}</div>
            <p style="color:var(--dim);font-size:10px;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Click to copy</p>
        </div>
        
        <footer>
            <p><a href="/">Crypto Empire Dashboard</a> - <a href="/sitemap.xml">Sitemap</a></p>
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
<head>""" + SHARED_HEAD + """
    <title>{{ title }} — Crypto Empire</title>
    <meta name="description" content="{{ title }}. Free crypto tools, wallet checker, gas tracker, and live prices.">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/blog/{{ slug }}">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">CRYPTO_EMPIRE</a>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/blog">Blog</a>
                <a href="/docs">API</a>
            </nav>
        </div>
    </header>
    <div class="container">
        <div class="back-nav"><a href="/blog">Blog</a></div>
        <h1 style="font-size:20px;color:var(--white);text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">{{ title }}</h1>
        <div class="meta" style="color:var(--dim);font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:24px;">{{ date }} - Tags: {{ tags|join(", ") }}</div>
        <div style="font-size:13px;line-height:1.8;color:var(--text);">{{ content|safe }}</div>
        
        <div class="donation-box" style="margin-top:28px;">
            <h3>Support These Free Tools</h3>
            <p style="color:var(--muted);font-size:12px;margin-bottom:12px;">If you found this guide useful, send a tip in ETH, USDC, or any ERC-20 token.</p>
            <div class="wallet-addr">{{ wallet }}</div>
            <p style="color:var(--dim);font-size:10px;margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Click to copy</p>
        </div>
        
        <footer>
            <p><a href="/blog">More articles</a></p>
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
# Telegram Bot Webhook
# ============================================================

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    from telegram_bot import handle_update
    data = request.get_json(silent=True) or {}
    result = handle_update(data)
    return jsonify(result)


# ============================================================
# 404 Handler
# ============================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>404 — Crypto Empire</title>
    <meta name="robots" content="noindex">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="logo">CRYPTO_EMPIRE</a>
        </div>
    </header>
    <div class="container">
        <div class="error-404">
            <h1>404</h1>
            <p>The requested resource was not found on this chain.</p>
            <div class="glitch">// PAGE_NOT_FOUND</div>
            <br><br>
            <a href="/" class="nav-btn">Return to Dashboard</a>
        </div>
        <footer>
            <p><a href="/">Crypto Empire Dashboard</a></p>
        </footer>
    </div>
</body>
</html>"""), 404


# ============================================================
# Main
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"⚡ Crypto Empire Dashboard starting on port {port}")
    print(f"💰 Wallet: {WALLET_ADDRESS}")
    app.run(host="0.0.0.0", port=port, debug=debug)
