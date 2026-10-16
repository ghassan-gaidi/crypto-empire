"""
Dominion Telegram Bot — Webhook mode for Vercel serverless
"""
import os
import json
import sqlite3
import logging
from html import unescape
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token from env (Vercel) or file (local dev)
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or ""
if not TELEGRAM_TOKEN:
    token_path = os.path.join(os.path.dirname(__file__), ".telegram_token")
    if os.path.exists(token_path):
        TELEGRAM_TOKEN = open(token_path).read().strip()

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ---------------------------------------------------------------------------
# Lazy import from app (avoid circular at module level)
# ---------------------------------------------------------------------------
_app_module = None

def _get_app():
    global _app_module
    if _app_module is None:
        import app as _app_module
    return _app_module

# ---------------------------------------------------------------------------
# Coin symbol → CoinGecko ID lookup for shortcut commands
# ---------------------------------------------------------------------------
SYMBOL_TO_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "matic": "polygon",
    "avax": "avalanche-2",
    "link": "chainlink",
    "bnb": "binancecoin",
    "atom": "cosmos",
    "trx": "tron",
    "ltc": "litecoin",
    "ton": "the-open-network",
    "arb": "arbitrum",
    "op": "optimism",
    "shib": "shiba-inu",
    "uni": "uniswap",
    "pepe": "pepe",
    "apt": "aptos",
    "sui": "sui",
    "near": "near",
    "fil": "filecoin",
    "algo": "algorand",
    "fld": "flow",
    "icp": "internet-computer",
    "egld": "elrond-erd-2",
    "inj": "injective-protocol",
    "sei": "sei-network",
    "tia": "celestia",
    "strk": "starknet",
    "wld": "worldcoin-wld",
    "poly": "polygon-ecosystem-token",
    "ondo": "ondo-finance",
    "pendle": "pendle",
    "ena": "ethena",
    "ethfi": "ether-fi",
    "rezt": "rezzle",
    "om": "mantra-dao",
    "rndr": "render-token",
    "aave": "aave",
    "mkr": "maker",
    "xlm": "stellar",
    "hbar": "hedera-hashgraph",
    "vet": "vechain",
    "ftm": "fantom",
    "cro": "crypto-com-chain",
    "grt": "the-graph",
    "imx": "immutable-x",
    "sand": "the-sandbox",
    "gala": "gala",
    "axs": "axie-infinity",
    "xtz": "tezos",
    "eos": "eos",
    # v3.7 expansion — meme coins, AI, DeFi
    "wif": "dogwifhat",
    "bonk": "bonk",
    "popcat": "popcat",
    "mew": "cat-in-a-dogs-world",
    "not": "notcoin",
    "jup": "jupiter",
    "pyth": "pyth-network",
    "fetch": "fetch-ai",
    "tao": "bittensor",
    "stx": "stacks",
    "rune": "thorchain",
    "kas": "kaspa",
    "ordi": "ordinals",
    "zro": "layerzero",
    "jto": "jito-governance-token",
    "hmstr": "hamster-kombat",
    "dogs": "dogs",
}

# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

def send_message(chat_id, text, parse_mode=None):
    """Send a plain or markdown message to a Telegram chat."""
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=8)
        return r.json()
    except Exception as e:
        log.error(f"send_message failed: {e}")
        return None

def send_typing(chat_id):
    """Show 'typing…' indicator."""
    try:
        requests.post(f"{API_BASE}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=3)
    except Exception:
        pass

def edit_message(chat_id, message_id, text):
    """Edit a previously sent message."""
    try:
        requests.post(f"{API_BASE}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": text
        }, timeout=5)
    except Exception:
        pass

def send_loading(chat_id, header):
    """Send a loading placeholder, return message_id (or None if failed)."""
    resp = send_message(chat_id, f">{header}\n{'═' * 18}\n\n  ⟳ Loading...")
    if resp and resp.get("ok"):
        return resp["result"]["message_id"]
    return None

def edit_or_send(chat_id, message_id, text):
    """Edit existing placeholder, or send fresh if editing fails."""
    if message_id:
        try:
            r = requests.post(f"{API_BASE}/editMessageText", json={
                "chat_id": chat_id, "message_id": message_id, "text": text
            }, timeout=5)
            if r.ok:
                return
        except Exception:
            pass
    send_message(chat_id, text)

# ---------------------------------------------------------------------------
# Formatting shortcuts
# ---------------------------------------------------------------------------
HEADER = "═" * 18
SEP = "─" * 18

def fmt_header(title):
    return f"> {title}\n{HEADER}"

def fmt_change(chg):
    if chg is None:
        return "N/A"
    arrow = "▲" if chg >= 0 else "▼"
    return f"{arrow} {abs(chg):.2f}%"

def fmt_price(price):
    if price is None or price == 0:
        return "N/A"
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:.8f}"

def fmt_market_cap(mc):
    if not mc:
        return "N/A"
    if mc >= 1e12:
        return f"${mc/1e12:.2f}T"
    if mc >= 1e9:
        return f"${mc/1e9:.2f}B"
    if mc >= 1e6:
        return f"${mc/1e6:.2f}M"
    return f"${mc:,.0f}"

# ---------------------------------------------------------------------------
# Chat type helpers
# ---------------------------------------------------------------------------

def is_group_chat(chat):
    """Check if a chat dict is a group/supergroup."""
    t = chat.get("type", "")
    return t in ("group", "supergroup")

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_start(chat_id, args=None, chat_type="private"):
    ref_code = args[0].lower().strip() if args and args[0].startswith("ref_") else None

    if ref_code:
        app = _get_app()
        referrer_code = ref_code[4:]
        if referrer_code and str(chat_id) not in referrer_code:
            app.record_referral(referrer_code, chat_id)

    # ASCII art banner
    banner = (
        "┌───────────────────────────┐\n"
        "│   CRYPTO EMPIRE  v3.7     │\n"
        "│   ──────────────────────  │\n"
        "│   56+ coin shortcuts      │\n"
        "│   @Crypt0Emp1reBot       │\n"
        "└───────────────────────────┘\n\n"
        "Live crypto data at your fingertips.\n\n"
    )
    intro = banner
    if chat_type == "group":
        intro += (
            "I reply to commands in this group.\n"
            "Just type /btc, /eth, /sol, etc. for instant prices.\n\n"
        )

    cmds = (
        "Commands:\n"
        "  📊 /price <coin>     — Price & 24h change\n"
        "  🪙 /btc /eth /sol    — Shortcuts for 55+ coins\n"
        "  ⛽ /gas              — Gas prices (ETH/Poly/Arb/Base)\n"
        "  😨 /fear             — Fear & Greed Index\n"
        "  🔥 /trending         — Top trending coins\n"
        "  🚀 /launches         — Upcoming token TGEs & IDOs\n"
        "  📰 /news             — Latest crypto headlines\n"
        "  👛 /wallet <addr>    — Multi-chain balance check\n"
        "  💱 /dexs             — Top DEXes by volume\n"
        "  🏦 /tvl              — Ethereum TVL\n"
        "  📉 /sparkline <coin> — 7d ASCII price chart\n"
        "  🐋 /whales           — On-chain whale moves >$100K\n"
        "  📈 /movers           — Top 24h gainers & losers\n"
        "  💰 /yields           — Top DeFi yield/APR pools\n"
        "  🔍 /profiler <addr>  — Wallet profiler (ETH + tokens)\n"
        "  🏆 /top              — Top coins by market cap\n"
        "  🔄 /convert <amt> <f> <t> — Crypto converter\n"
        "  🌐 /global          — Global market overview\n"
        "  📂 /categories      — Top crypto categories\n"
        "  🔔 /alerts           — Your active price alerts\n"
        "  ⭐ /premium          — Unlock premium features\n"
        "  ⚙️  /manage           — Manage subscription\n"
        "  🔗 /referral         — Referral link & rewards\n"
        "  ☕ /donate           — Support development\n"
        "  ❓ /help             — This message\n\n"
        "Built autonomously — github.com/ghassan-gaidi/crypto-empire"
    )

    if chat_type == "private":
        app = _get_app()
        code = app.get_or_create_ref_code(chat_id)
        bot_username = os.environ.get("BOT_USERNAME", "Crypt0Emp1reBot")
        cmds += (
            f"\n\n💎 Referral Program — Earn Free Premium!\n"
            f"Invite friends to add me to their groups.\n"
            f"3 referrals = 1 free month of Premium!\n\n"
            f"Your referral link:\n"
            f"https://t.me/{bot_username}?start=ref_{code}\n\n"
            f"Or add me to a group:\n"
            f"https://t.me/{bot_username}?startgroup=ref_{code}"
        )

    if chat_type == "group":
        cmds += (
            "\n\nTip: Add me to more groups and use /btc /eth /sol "
            "for quick prices anywhere."
        )

    if ref_code:
        cmds += "\n\n✅ Referral recorded! Thanks for spreading the word."

    send_message(chat_id, intro + cmds)

def cmd_price(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /price <coin_id>  (e.g. /price bitcoin)\nTip: use /btc, /eth, /sol shortcuts.")
        return
    coin = args[0].lower().strip()
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin in data:
        d = data[coin]
        usd = d.get("usd", 0)
        chg = d.get("usd_24h_change")
        mc = d.get("usd_market_cap", 0)
        vol = d.get("usd_24h_vol", 0)
        msg = (
            f"  {coin.upper()}\n"
            f"  {HEADER}\n\n"
            f"  Price  │ {fmt_price(usd)}\n"
            f"  24h    │ {fmt_change(chg)}\n"
            f"  M.Cap  │ {fmt_market_cap(mc)}\n"
            f"  Vol    │ {fmt_market_cap(vol)}"
        )
    else:
        msg = f"Coin '{coin}' not found. Try /price bitcoin."
    send_message(chat_id, msg)

def cmd_gas(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price = ""
    if data and "ethereum" in data:
        eth_price = f"ETH: ${data['ethereum']['usd']:,.0f}\n"
    chains = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon":  "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "base":     "https://mainnet.base.org",
    }
    lines = [fmt_header("GAS TRACKER")]
    if eth_price:
        lines.append(f"\n{eth_price.strip()}")
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=5)
            res = r.json()
            if "result" in res:
                gwei = int(res["result"], 16) / 1e9
                lines.append(f"{name:<10} {gwei:.1f} gwei")
            else:
                lines.append(f"{name:<10} error")
        except Exception:
            lines.append(f"{name:<10} error")
    send_message(chat_id, "\n".join(lines))

def cmd_fear(chat_id, args=None):
    app = _get_app()
    data = app.fetch_sync("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data and data["data"]:
        d = data["data"][0]
        val = d.get("value", "?")
        cls = d.get("value_classification", "N/A")
        arrow = "📈" if int(val) > 50 else "📉" if int(val) < 25 else "➕"
        msg = f"{fmt_header('FEAR & GREED')}\n\nValue: {val}/100\nState: {cls.upper()} {arrow}"
    else:
        msg = "Fear & Greed unavailable"
    send_message(chat_id, msg)

def cmd_trending(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/search/trending")
    if data and "coins" in data:
        lines = [fmt_header("TRENDING COINS")]
        for i, coin in enumerate(data["coins"][:10], 1):
            item = coin.get("item", {})
            name = item.get("name", "?")
            sym = (item.get("symbol") or "").upper()
            rank = item.get("market_cap_rank") or "--"
            lines.append(f"{i:2}. {name} ({sym}) — Rank #{rank}")
        msg = "\n".join(lines)
    else:
        msg = "Trending unavailable"
    send_message(chat_id, msg)

def cmd_launches(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/launches")
    if data and "launches" in data:
        launches = data["launches"]
        lines = [fmt_header("TOKEN LAUNCH CALENDAR")]
        upcoming = [l for l in launches if l["status"] == "upcoming"][:5]
        if upcoming:
            for l in upcoming:
                dd = l.get("days_until", "?")
                lines.append(f"\n📅 {l['name']} (${l['symbol']})")
                lines.append(f"   {l['type']} — {dd} days · {l['chain']}")
        else:
            lines.append("\nNo upcoming launches right now.")
        msg = "\n".join(lines)
    else:
        msg = "Launch calendar unavailable. See https://crypto-empire-ten.vercel.app/launches"
    send_message(chat_id, msg)

def cmd_news(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    items = app.fetch_rss("https://cointelegraph.com/rss")
    if items:
        lines = [fmt_header("CRYPTO NEWS")]
        for item in items[:5]:
            lines.append(f"\n• {item['title']}")
            if item.get('date'):
                lines.append(f"  {item['date'][:16]}")
        msg = "\n".join(lines)
    else:
        msg = "News unavailable"
    send_message(chat_id, msg)

def cmd_wallet(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /wallet <0x address>")
        return
    addr = args[0].strip()
    if not addr.startswith("0x"):
        send_message(chat_id, "Invalid address — must start with 0x")
        return
    send_typing(chat_id)
    app = _get_app()
    price_data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids=ethereum,matic-network&vs_currencies=usd")
    eth_p = (price_data or {}).get("ethereum", {}).get("usd", 0)
    matic_p = (price_data or {}).get("matic-network", {}).get("usd", 0)
    chains = {
        "Ethereum": "https://ethereum-rpc.publicnode.com",
        "Arbitrum": "https://arb1.arbitrum.io/rpc",
        "Base":     "https://mainnet.base.org",
        "Polygon":  "https://polygon-rpc.com",
    }
    total = 0
    lines = [fmt_header("WALLET"), "", f"{addr[:10]}...{addr[-6:]}"]
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_getBalance","params":[addr,"latest"],"id":1}, timeout=6)
            res = r.json()
            if "result" in res:
                bal = int(res["result"], 16) / 1e18
                price = eth_p if name != "Polygon" else matic_p
                usd = bal * price
                total += usd
                bal_s = f"{bal:.4f}" if bal >= 0.001 else f"{bal:.8f}"
                lines.append(f"\n{name:<10} {bal_s}  ${usd:,.2f}")
            else:
                lines.append(f"\n{name:<10} error")
        except Exception:
            lines.append(f"\n{name:<10} error")
    lines.append(f"\n{SEP}")
    lines.append(f"TOTAL: ${total:,.2f}")
    send_message(chat_id, "\n".join(lines))

def cmd_tvl(chat_id, args=None):
    app = _get_app()
    data = app.fetch_sync("https://api.llama.fi/v2/historicalChainTvl/Ethereum")
    if data and len(data) > 0:
        latest = data[-1]
        tvl_b = latest.get("tvl", 0) / 1e9
        msg = f"{fmt_header('ETH TVL')}\n\n${tvl_b:.2f}B\nSource: DeFiLlama"
    else:
        msg = "TVL unavailable"
    send_message(chat_id, msg)

def cmd_dexs(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://api.llama.fi/overview/dexs")
    if data and "protocols" in data:
        top = sorted(data["protocols"], key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:10]
        lines = [fmt_header("TOP DEXES (24h Vol)")]
        for i, d in enumerate(top, 1):
            name = d.get("displayName") or d.get("name", "?")
            vol = d.get("total24h", 0) or 0
            vol_s = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K"
            chg = d.get("change_1d", 0) or 0
            arrow = "▲" if chg >= 0 else "▼"
            lines.append(f"{i:2}. {name:<20} {vol_s:>10} {arrow}{chg:+.1f}%")
        msg = "\n".join(lines)
    else:
        msg = "DEX data unavailable"
    send_message(chat_id, msg)

def cmd_whales(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "WHALE TRACKER")
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/whales?limit=5")
    if data and "moves" in data and data["moves"]:
        lines = [fmt_header("WHALE TRACKER")]
        for m in data["moves"]:
            usd = f"${m['usdValue']:,.0f}" if m.get("usdValue") else f"{m['value']:,.2f}"
            addr_s = f"{m['to'][:6]}...{m['to'][-4:]}"
            lines.append(f"\n🐋 {usd} {m['token']}")
            lines.append(f"   → {addr_s}  · {m['txHash'][:8]}...")
        lines.append(f"\n{SEP}")
        lines.append(f"Updated: {data['lastUpdated'][:19]} UTC")
        lines.append("Tracked: USDT/USDC/WBTC · crypto-empire-ten.vercel.app/whales")
        msg = "\n".join(lines)
    else:
        msg = "No whale moves found right now."
    edit_or_send(chat_id, msg_id, msg)

def cmd_premium(chat_id, args=None):
    send_typing(chat_id)
    msg = (
        f"{fmt_header('CRYPTO EMPIRE PREMIUM')}\n\n"
        "Unlock premium features:\n\n"
        "• Telegram whale alerts — real-time $100K+ push\n"
        "• Multi-wallet portfolio — track 6+ ETH addresses\n"
        "• Priority price alerts — instant threshold notifications\n"
        "• Premium sentiment indicators — buy/sell signals\n"
        "• Ad-free across all pages\n"
        "• Support development\n\n"
        "👉 Subscribe:\n"
        "https://buy.polar.sh/polar_cl_6tzQXPw5VwincKlZdlyR2aM9XGePVbhfzWCb13P42ox\n\n"
        "Price: $9.99/month — Cancel anytime\n"
        "Powered by Polar.sh\n\n"
        "Already subscribed? Manage at:\n"
        "https://crypto-empire-ten.vercel.app/premium\n\n"
        "☕ Like the bot? Donate ETH:\n"
        "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef"
    )
    send_message(chat_id, msg)

def cmd_manage(chat_id, args=None):
    send_typing(chat_id)
    url = f"https://crypto-empire-ten.vercel.app/premium?customer_id={chat_id}"
    msg = (
        f"{fmt_header('MANAGE SUBSCRIPTION')}\n\n"
        "Open the web portal to view, upgrade, or cancel:\n\n"
        f"{url}\n\n"
        "Note: Your Telegram ID links your subscription."
    )
    send_message(chat_id, msg)

def cmd_referral(chat_id, args=None):
    app = _get_app()
    code = app.get_or_create_ref_code(chat_id)
    stats = app.get_ref_stats(chat_id)
    bot_username = os.environ.get("BOT_USERNAME", "Crypt0Emp1reBot")
    refs = stats["referred_count"]
    rewards = stats["rewards_earned"]
    next_reward = 3 - (refs % 3) if refs % 3 != 0 else 3
    has_premium = app._is_premium(str(chat_id))
    msg = (
        f"{fmt_header('REFERRAL PROGRAM')}\n\n"
        f"Your referrals: {refs}\n"
        f"Premium months earned: {rewards}\n"
        f"Next reward in: {next_reward} more referrals\n\n"
        "🎁 3 referrals = 1 free month of Premium\n\n"
        "Your unique referral link:\n"
        f"https://t.me/{bot_username}?start=ref_{code}\n\n"
        "Add me to your group:\n"
        f"https://t.me/{bot_username}?startgroup=ref_{code}\n\n"
    )
    if not has_premium:
        msg += "Already subscribed? Share your link and earn free months!"
    else:
        msg += "You're premium already — each reward extends your subscription by 1 month."
    send_message(chat_id, msg)

def cmd_donate(chat_id, args=None):
    send_typing(chat_id)
    msg = (
        f"{fmt_header('SUPPORT DEVELOPMENT')}\n\n"
        "All tools are free. If you find this bot useful, consider a donation.\n\n"
        "ETH / BSC / POLYGON / ARBITRUM / BASE:\n"
        "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef\n\n"
        "BITCOIN:\n"
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh\n\n"
        "Every donation keeps the bot running. Thank you."
    )
    send_message(chat_id, msg)

def cmd_sparkline(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /sparkline <coin_id>  (e.g. /sparkline bitcoin)")
        return
    coin = args[0].lower().strip()
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/coins/{coin}?localization=false&tickers=false&community_data=false&developer_data=false&sparkline=true")
    if data and "market_data" in data:
        prices = data.get("market_data", {}).get("sparkline_7d", {}).get("price", [])
        if prices and len(prices) > 1:
            bars = 30
            step = len(prices) / bars
            sample = [prices[min(int(i * step), len(prices) - 1)] for i in range(bars)]
            mn, mx = min(sample), max(sample)
            rng = mx - mn if mx > mn else 1
            h = 8
            rows = []
            for row in range(h - 1, -1, -1):
                threshold = mn + (row / (h - 1)) * rng
                line = ""
                for p in sample:
                    line += "█" if p >= threshold else " "
                rows.append(line)
            chart = "\n".join(rows)
            arrow = " ▲" if sample[-1] >= sample[0] else " ▼"
            price_s = fmt_price(sample[-1])
            msg = f"{fmt_header(f'{coin.upper()} 7d{arrow}')}\n{'─' * 20}\n{chart}\n{'─' * 20}\n{price_s}"
        else:
            msg = f"No sparkline data for {coin}"
    else:
        msg = f"Coin '{coin}' not found"
    send_message(chat_id, msg)

# ---------------------------------------------------------------------------
# New command handlers (v3.5 expansion)
# ---------------------------------------------------------------------------

def cmd_movers(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "MARKET MOVERS")
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/movers")
    if data and data.get("top_gainers"):
        g = data["top_gainers"][:5]
        l = data["top_losers"][:5]
        lines = [fmt_header("MARKET MOVERS (24h)")]
        lines.append("\n🏆 TOP GAINERS")
        for c in g:
            sym = (c.get("symbol") or "").upper()
            chg = c.get("change", 0) or 0
            p = c.get("price", "?")
            lines.append(f"  {sym:<6} ▲ {chg:.2f}%  ${p}")
        lines.append("\n💩 TOP LOSERS")
        for c in l:
            sym = (c.get("symbol") or "").upper()
            chg = c.get("change", 0) or 0
            p = c.get("price", "?")
            lines.append(f"  {sym:<6} ▼ {abs(chg):.2f}%  ${p}")
        msg = "\n".join(lines)
    else:
        msg = "Movers unavailable right now."
    edit_or_send(chat_id, msg_id, msg)

def cmd_yields(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "YIELD AGGREGATOR")
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/yields")
    if data:
        lines = [fmt_header("YIELD AGGREGATOR")]
        for cat in ["lending", "stablecoin"]:
            pools = data.get(cat, [])[:3]
            if pools:
                lines.append(f"\n═══ {cat.upper()} ═══")
                for p in pools:
                    apy = p.get("apy", 0) or 0
                    sym = p.get("symbol", "?")
                    chain = p.get("chain", "?")
                    tvl = p.get("tvlUsd", 0) or 0
                    tvl_s = f"${tvl/1e6:.1f}M" if tvl >= 1e6 else f"${tvl/1e3:.0f}K"
                    lines.append(f"  {sym:<8} {apy:.2f}% | {chain} | {tvl_s}")
        lines.append(f"\n{SEP}")
        lines.append("crypto-empire-ten.vercel.app/yields")
        msg = "\n".join(lines)
    else:
        msg = "Yields unavailable."
    edit_or_send(chat_id, msg_id, msg)

def cmd_profiler(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /profiler <0x address>")
        return
    addr = args[0].strip()
    if not addr.startswith("0x"):
        send_message(chat_id, "Invalid address — must start with 0x")
        return
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "WALLET PROFILER")
    app = _get_app()
    data = app.fetch_sync(f"https://crypto-empire-ten.vercel.app/api/profiler/{addr}")
    if data:
        eth_bal = data.get("ethBalance", "0")
        usd_val = data.get("totalUsdValue", 0) or 0
        tokens = data.get("tokens", [])
        tx_count = data.get("txCount", "?")
        lines = [
            fmt_header("WALLET PROFILER"),
            "",
            f"{addr[:10]}...{addr[-6:]}",
            "",
            f"ETH:  {eth_bal}  ${usd_val:,.2f}",
            f"TXs:  {tx_count}",
        ]
        if tokens:
            lines.append(f"\nTOKENS:")
            for t in tokens[:8]:
                sym = t.get("symbol", "?")
                bal = t.get("balance", "0")
                val = t.get("usdValue", 0) or 0
                lines.append(f"  {sym:<8} {bal}  ${val:,.2f}")
        msg = "\n".join(lines)
    else:
        msg = f"Profiler unavailable for {addr[:10]}..."
    edit_or_send(chat_id, msg_id, msg)

def cmd_top(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "TOP COINS")
    app = _get_app()
    data = app.fetch_sync(
        f"{app.COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&sparkline=false"
    )
    if data:
        lines = [fmt_header("TOP COINS (by Market Cap)")]
        for i, c in enumerate(data, 1):
            sym = (c.get("symbol") or "").upper()
            p = c.get("current_price", 0) or 0
            chg = c.get("price_change_percentage_24h", 0) or 0
            mc = c.get("market_cap", 0) or 0
            arrow = "▲" if chg >= 0 else "▼"
            p_s = f"${p:,.2f}" if p >= 1 else f"${p:.8f}" if p else "N/A"
            lines.append(f"{i:2}. {sym:<6} {p_s}  {arrow}{abs(chg):.2f}%")
        msg = "\n".join(lines)
    else:
        msg = "Top coins unavailable."
    edit_or_send(chat_id, msg_id, msg)

def cmd_convert(chat_id, args):
    if len(args) < 3:
        send_message(chat_id, "Usage: /convert <amount> <from> <to>\n  e.g., /convert 1 btc usd")
        return
    try:
        amount = float(args[0])
    except ValueError:
        send_message(chat_id, "Invalid amount.")
        return
    from_coin = args[1].lower()
    to_currency = args[2].lower()
    send_typing(chat_id)
    app = _get_app()
    alias = {"usd": "usd", "usdt": "tether", "usdc": "usd-coin",
             "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
             "bnb": "binancecoin", "xrp": "xrp", "ada": "cardano"}
    from_id = alias.get(from_coin, from_coin)
    to_id = alias.get(to_currency, to_currency)
    ids = [from_id]
    if to_id not in ("usd", from_id):
        ids.append(to_id)
    price_data = app.fetch_sync(
        f"{app.COINGECKO_API}/simple/price?ids={','.join(ids)}&vs_currencies=usd"
    )
    if not price_data:
        send_message(chat_id, f"Could not fetch price for {from_coin}.")
        return
    from_usd = (price_data.get(from_id) or {}).get("usd", 0)
    if from_usd == 0:
        send_message(chat_id, f"Could not find '{from_coin}'.")
        return
    from_total = amount * from_usd
    if to_currency in ("usd",):
        msg = f"{fmt_header('CONVERT')}\n\n{amount} {from_coin.upper()} = ${from_total:,.2f}"
    else:
        to_usd = (price_data.get(to_id) or {}).get("usd", 0)
        if to_usd == 0:
            send_message(chat_id, f"Could not find '{to_currency}'.")
            return
        result = from_total / to_usd
        msg = f"{fmt_header('CONVERT')}\n\n{amount} {from_coin.upper()} = {result:,.6f} {to_currency.upper()}"
    send_message(chat_id, msg)

def cmd_alerts(chat_id, args=None):
    app = _get_app()
    conn = sqlite3.connect(str(app.DB_PATH))
    try:
        cur = conn.execute(
            "SELECT coin, target_price, chat_id FROM alerts WHERE chat_id = ? ORDER BY created_at DESC",
            (str(chat_id),)
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    if not rows:
        msg = (
            f"{fmt_header('PRICE ALERTS')}\n\n"
            "No active alerts.\n\n"
            "Set alerts on the dashboard:\n"
            "https://crypto-empire-ten.vercel.app/#alerts\n\n"
            "Premium users get priority alert delivery."
        )
    else:
        lines = [fmt_header(f"YOUR ALERTS ({len(rows)})")]
        for coin, price, _ in rows[:10]:
            lines.append(f"\n{coin.upper()} → ${price}")
        msg = "\n".join(lines)
    send_message(chat_id, msg)

# ---------------------------------------------------------------------------
# v3.7 expansion — global market + categories
# ---------------------------------------------------------------------------

def cmd_global(chat_id, args=None):
    """Global crypto market overview: total cap, volume, BTC dominance."""
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "GLOBAL MARKET")
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/global")
    if data and "data" in data:
        d = data["data"]
        active = d.get("active_cryptocurrencies", "?")
        total_mc = d.get("total_market_cap", {}).get("usd", 0)
        total_vol = d.get("total_volume", {}).get("usd", 0)
        btc_dom = d.get("market_cap_percentage", {}).get("btc", 0)
        eth_dom = d.get("market_cap_percentage", {}).get("eth", 0)
        mc_chg = d.get("market_cap_change_percentage_24h_usd", 0) or 0
        exchanges = d.get("markets", "?")
        def fmt_b(n):
            if n >= 1e12: return f"${n/1e12:.2f}T"
            if n >= 1e9:  return f"${n/1e9:.2f}B"
            return f"${n:,.0f}"
        arrow = "▲" if mc_chg >= 0 else "▼"
        lines = [
            fmt_header("GLOBAL MARKET"),
            "",
            f"Active coins: {active}",
            f"Exchanges:    {exchanges}",
            "",
            f"Market Cap:   {fmt_b(total_mc)}",
            f"24h Volume:   {fmt_b(total_vol)}",
            f"24h Change:   {arrow}{abs(mc_chg):.2f}%",
            "",
            f"BTC Dominance: {btc_dom:.1f}%",
            f"ETH Dominance: {eth_dom:.1f}%",
        ]
        msg = "\n".join(lines)
    else:
        msg = "Global market data unavailable."
    edit_or_send(chat_id, msg_id, msg)

def cmd_categories(chat_id, args=None):
    """Top crypto categories by market cap from CoinGecko."""
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "CATEGORIES")
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/coins/categories")
    if data and isinstance(data, list):
        sorted_cats = sorted(data, key=lambda x: x.get("market_cap", 0) or 0, reverse=True)[:12]
        lines = [fmt_header("TOP CATEGORIES (by Market Cap)")]
        for i, c in enumerate(sorted_cats, 1):
            name = c.get("name", "?")
            mc = c.get("market_cap", 0) or 0
            chg = c.get("market_cap_change_24h", 0) or 0
            if mc >= 1e9:
                mc_s = f"${mc/1e9:.1f}B"
            elif mc >= 1e6:
                mc_s = f"${mc/1e6:.1f}M"
            else:
                mc_s = f"${mc:,.0f}"
            arrow = "▲" if chg >= 0 else "▼"
            lines.append(f"{i:2}. {name:<20} {mc_s:>8}  {arrow}{abs(chg):.1f}%")
        msg = "\n".join(lines)
    else:
        msg = "Categories data unavailable."
    edit_or_send(chat_id, msg_id, msg)

# ---------------------------------------------------------------------------
# Group event handlers
# ---------------------------------------------------------------------------

def handle_my_chat_member(data):
    """Handle bot being added to or removed from a group."""
    chat = data.get("chat", {})
    chat_id = chat.get("id")
    new_status = data.get("new_chat_member", {}).get("status", "")
    old_status = data.get("old_chat_member", {}).get("status", "")

    if not chat_id:
        return {"ok": False, "reason": "no chat"}

    group_title = chat.get("title", "this group")
    chat_type = chat.get("type", "unknown")

    if new_status == "member" and old_status in ("left", "kicked", "restricted"):
        # Bot was added to group
        bot_username = os.environ.get("BOT_USERNAME", "Crypt0Emp1reBot")
        welcome = (
            f"🤖 *Dominion Bot added to {group_title}*\n\n"
            f"Type /btc, /eth, /sol or any coin ticker for instant prices.\n"
            f"Use /help to see all commands.\n\n"
            f"More at crypto-empire-ten.vercel.app\n\n"
            f"💎 *Earn Free Premium*\n"
            f"Share this link with friends to earn rewards:\n"
            f"https://t.me/{bot_username}?start=ref_your_code\n"
            f"3 referrals = 1 free month!"
        )
        send_message(chat_id, welcome, parse_mode="Markdown")
        log.info(f"Bot added to group: {group_title} ({chat_id})")

    elif new_status == "left" and old_status == "member":
        # Bot was removed from group
        log.info(f"Bot removed from group: {group_title} ({chat_id})")

    return {"ok": True}

def store_username_mapping(username, chat_id):
    """Store chat_id → username mapping for alert delivery."""
    if not username or not chat_id:
        return
    try:
        app = _get_app()
        conn = sqlite3.connect(str(app.DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS telegram_mapping (username TEXT PRIMARY KEY, chat_id INTEGER)")
        conn.execute(
            "INSERT OR REPLACE INTO telegram_mapping (username, chat_id) VALUES (?, ?)",
            (username, chat_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "start":     cmd_start,
    "help":      cmd_start,
    "price":     cmd_price,
    "gas":       cmd_gas,
    "fear":      cmd_fear,
    "feargreed": cmd_fear,
    "trending":  cmd_trending,
    "launches":  cmd_launches,
    "launch":    cmd_launches,
    "news":      cmd_news,
    "wallet":    cmd_wallet,
    "tvl":       cmd_tvl,
    "dexs":      cmd_dexs,
    "dex":       cmd_dexs,
    "sparkline": cmd_sparkline,
    "whales":    cmd_whales,
    "whale":     cmd_whales,
    "premium":   cmd_premium,
    "subscribe": cmd_premium,
    "manage":    cmd_manage,
    "referral":  cmd_referral,
    "ref":       cmd_referral,
    "affiliate": cmd_referral,
    "donate":    cmd_donate,
    "donation":  cmd_donate,
    "support":   cmd_donate,
    "movers":    cmd_movers,
    "gainers":   cmd_movers,
    "losers":    cmd_movers,
    "yields":    cmd_yields,
    "yield":     cmd_yields,
    "apy":       cmd_yields,
    "profiler":  cmd_profiler,
    "top":       cmd_top,
    "convert":   cmd_convert,
    "conv":      cmd_convert,
    "alerts":    cmd_alerts,
    "alert":     cmd_alerts,
    "myalerts":  cmd_alerts,
    # v3.7 expansion
    "global":    cmd_global,
    "market":    cmd_global,
    "categories": cmd_categories,
    "cats":      cmd_categories,
    "sectors":   cmd_categories,
}

# Register shortcut commands (e.g., /btc → cmd_price(["bitcoin"]))
for sym, cg_id in SYMBOL_TO_ID.items():
    COMMANDS[sym] = lambda chat_id, args, cg_id=cg_id: cmd_price(chat_id, [cg_id])

def handle_update(data):
    """Parse a Telegram webhook update and execute the command."""
    chat_id = None
    try:
        # Handle group membership events
        my_chat_member = data.get("my_chat_member")
        if my_chat_member:
            return handle_my_chat_member(my_chat_member)

        msg = data.get("message", {})
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip()
        if not chat_id or not text:
            return {"ok": False, "reason": "no message"}

        chat_type = chat.get("type", "private")

        # Store chat_id → username mapping for alert delivery
        user = msg.get("from", {})
        username = (user.get("username") or "").lower().strip()
        store_username_mapping(username, chat_id)

        # Parse command
        parts = text.split()
        cmd = parts[0].lower().lstrip("/").split("@")[0]  # strip / and bot username
        args = parts[1:]

        handler = COMMANDS.get(cmd)
        if handler:
            # Pass chat_type to cmd_start for group-specific messaging
            if cmd in ("start", "help"):
                handler(chat_id, args, chat_type=chat_type)
            else:
                handler(chat_id, args)
        else:
            # In groups, offer helpful suggestions for unknown commands
            suggestions = ""
            if chat_type in ("group", "supergroup"):
                suggestions = "\n\nTry /btc, /eth, /sol for prices, or /help for all commands."
            send_message(chat_id, f"Unknown command: /{cmd}{suggestions}")
        return {"ok": True}
    except Exception as e:
        log.exception("handle_update error")
        if chat_id:
            send_message(chat_id, f"Error: {str(e)[:200]}")
        return {"ok": False, "error": str(e)}
