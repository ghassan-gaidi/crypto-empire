# ⛰️ Dominion — Autonomous Crypto Intelligence

> **Live market dashboard + Telegram bot with 50+ commands, whale tracking, and premium monetization.**

[![Live](https://img.shields.io/badge/live-crypto--empire--ten.vercel.app-black)](https://crypto-empire-ten.vercel.app)
[![Bot](https://img.shields.io/badge/TG-%40Crypt0Emp1reBot-26A5E4)](https://t.me/Crypt0Emp1reBot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000)](https://flask.palletsprojects.com)
[![Polar](https://img.shields.io/badge/premium-Polar.sh-DC2626)](https://polar.sh)

---

## 🎯 What It Does

Dominion is a **two-in-one crypto intelligence system**:

1. **🌐 Web Dashboard** — Live prices, gas tracker, whale moves, DEX volumes, portfolio tracking, yield aggregation, token launch calendar — all at `crypto-empire-ten.vercel.app`
2. **🤖 Telegram Bot** — 50+ commands via `@Crypt0Emp1reBot` — price lookups, gas checks, wallet profiling, whale alerts, and more

---

## 🔥 Dashboard Features

### 📊 Live Market Intelligence
- **Top 20 Cryptos** — rank, price, 24h%, 7d%, sparkline SVG, market cap, volume
- **Multi-chain Gas Tracker** — real-time Ethereum, Polygon, Arbitrum, Base (polls every 30s)
- **Fear & Greed Index** — 7-day history with classification
- **Trending Coins** — top 10 on CoinGecko with live prices
- **Market Movers** — 24h gainers & losers with price/change

### 🔍 On-Chain Tools
- **Wallet Checker** — check any ETH address across Ethereum, Arbitrum, Base, Polygon
- **Wallet Profiler** — deep inspection: ETH balance, tx count, top 11 ERC-20 tokens, USD values
- **Portfolio Tracker** — create named portfolios (up to 5 addresses free, unlimited premium). Auto P&L tracking with shareable URLs.
- **Whale Tracker** — real-time USDT/USDC/WBTC transfers >$100K on Ethereum (refreshes every 5 min)

### 📈 DeFi & Markets
- **DEX Volume Rankings** — top 10 DEXes by 24h volume (DeFiLlama)
- **Yield Aggregator** — curated pools: lending, staking, stablecoin yields, filterable by APY/chain/TVL
- **Token Launch Calendar** — upcoming IDOs/ICOs/TGEs with countdown timers
- **Live Crypto News** — latest from CoinTelegraph RSS

### 💰 Monetization
- **Premium subscription** — $9.99/month via Polar.sh
- **Ad placement system** — banner slots with CRUD admin API
- **Sponsored coin spotlight** — paid placements with live price
- **Affiliate links** — Binance, Coinbase, Kraken, Bybit, OKX, KuCoin, Gate.io, Uniswap, Ledger, Trezor, Crypto.com
- **Donation system** — BTC + ETH addresses

---

## 🤖 Telegram Bot (@Crypt0Emp1reBot)

| Command | Description |
|---------|-------------|
| `/price <coin>` / `/btc` `/eth` `/sol` | Instant price lookup for 80+ symbols |
| `/gas` | Live multi-chain gas prices |
| `/fear` | Fear & Greed Index |
| `/trending` | Top 10 trending coins |
| `/news` | Latest 5 crypto headlines |
| `/wallet <0x>` | Multi-chain balance check |
| `/whales` | Recent $100K+ on-chain moves |
| `/profiler <0x>` | Deep wallet analysis |
| `/portfolio` | Multi-wallet portfolio tracker |
| `/yields` | Yield aggregator |
| `/launches` | Upcoming TGE/IDO calendar |
| `/convert 1 BTC USD` | Crypto converter |
| `/premium` | Subscribe to premium |

**Premium-only:** Real-time whale alerts · Unlimited portfolio wallets · Priority price alerts · Buy/sell sentiment signals · Ad-free

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│               Vercel (Primary)                   │
│  ┌──────────────────────────────────────────┐    │
│  │          Flask App (app.py)              │    │
│  │  Dashboard  TG Webhook  Polar Webhook    │    │
│  │  REST API   Admin CRUD  Whale Cache      │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────┐
│          Home Server (Systemd)                  │
│  ┌──────────────────────────────────────────┐   │
│  │   bot.py — Telegram polling mode          │   │
│  │   dominion-bot.service — always-on daemon │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────┐
│          GitHub Actions (Cron)                   │
│  ┌────────┐ ┌────────────┐ ┌────────────────┐   │
│  │Monitor │ │Whale Tracker│ │Check Alerts    │   │
│  │30min   │ │5min         │ │15min           │   │
│  └────────┘ └────────────┘ └────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Choice |
|-------|--------|
| **Backend** | Python 3.11, Flask 3.0, Gunicorn |
| **Frontend** | Server-side Jinja2 + vanilla JS, no framework |
| **Data APIs** | CoinGecko, DeFiLlama, Alternative.me, CoinTelegraph |
| **On-chain** | Public Ethereum RPCs (`eth_gasPrice`, `eth_call`, `eth_getBalance`) |
| **Telegram** | python-telegram-bot (polling + webhook dual mode) |
| **Payments** | Polar.sh ($9.99/mo) — full webhook verification |
| **Database** | SQLite (price cache, alerts, subscriptions) |
| **Deploy** | Vercel (web) + Systemd daemon (TG bot) |
| **CI** | 4 GitHub Actions workflows (monitor, whales, alerts, distribution) |
| **Design** | Void dark (#08080E) + Crimson (#DC2626), Space Grotesk + JetBrains Mono, sharp 4px corners |

---

## 📊 API (30+ Endpoints)

All dashboard data is exposed as public REST API:

```
/price/<coin>   /trending   /gas   /fear-greed   /news
/tvl            /dexs       /movers            /whales
/wallet/<addr>  /profiler/<addr>              /portfolio
/yields         /launches   /alerts            /health
/premium/checkout /premium/webhook            /premium/check
```

Free tier: 100 req/day · Premium: 10K req/day

---

## 📊 Status

- **Version:** v3.4
- **Deploy:** Live at crypto-empire-ten.vercel.app
- **Bot:** `@Crypt0Emp1reBot` — always on
- **Revenue:** $0 (no subscribers yet)
- **Monitoring:** 4 GH Actions workflows keep everything running

---

## 🧠 Skills Demonstrated

`Python` `Flask` `REST API Design` `Telegram Bot (50+ commands)` `CoinGecko API` `DeFiLlama` `On-chain RPC` `Whale Tracking` `Polar.sh Integration` `SQLite` `Vercel Deployment` `Systemd Daemon` `GitHub Actions` `Brutalist Design`

> *Build your own Bloomberg Terminal for crypto — then sell access.*
