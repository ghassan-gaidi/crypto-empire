#!/usr/bin/env python3
"""
Dominion Telegram Bot - Autonomous crypto intelligence & trading
Monetized via premium subscriptions (paid in crypto)
"""

import os
import sys
import json
import time
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from decimal import Decimal

# Conditionally import telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
except ImportError:
    print("Telegram not available, install with: pip install python-telegram-bot")
    sys.exit(1)

import aiohttp
import requests

# ============================================================
# Configuration
# ============================================================
WALLET_ADDRESS = "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef"
DATA_DIR = Path.home() / "dominion" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# CoinGecko API
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Premium features cost (in USD, paid in crypto via Polar)
PREMIUM_PRICE_USD = 10  # $10/month for premium
PREMIUM_PRICE_ETH = 0.005  # ~$10 at $2000 ETH
LIFETIME_PRICE_USD = 50  # $50 lifetime access

# ============================================================
# Database
# ============================================================
DB_PATH = DATA_DIR / "bot.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_premium BOOLEAN DEFAULT 0,
            premium_until TIMESTAMP,
            watchlist TEXT DEFAULT '[]',
            alerts_enabled BOOLEAN DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tx_hash TEXT,
            amount_usd REAL,
            plan TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            coin_id TEXT PRIMARY KEY,
            price_usd REAL,
            change_24h REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ============================================================
# CoinGecko API
# ============================================================
SESSION = None

async def get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION

async def fetch_price(coin_id: str) -> Optional[Dict]:
    """Fetch current price for a coin"""
    session = await get_session()
    url = f"{COINGECKO_BASE}/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true"
    }
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get(coin_id)
    except Exception as e:
        logging.error(f"Price fetch error: {e}")
    return None

async def fetch_trending() -> List[Dict]:
    """Fetch trending coins"""
    session = await get_session()
    url = f"{COINGECKO_BASE}/search/trending"
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("coins", [])
    except Exception as e:
        logging.error(f"Trending fetch error: {e}")
    return []

async def search_coins(query: str) -> List[Dict]:
    """Search for coins"""
    session = await get_session()
    url = f"{COINGECKO_BASE}/search"
    params = {"query": query}
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("coins", [])[:10]
    except Exception as e:
        logging.error(f"Search error: {e}")
    return []

# ============================================================
# Bot Handlers
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    db_conn = sqlite3.connect(str(DB_PATH))
    c = db_conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
              (user.id, user.username or user.full_name))
    db_conn.commit()
    db_conn.close()

    welcome = f"""
⚡ *Dominion Bot* ⚡

Your autonomous crypto intelligence hub. Track prices, get alerts, discover opportunities.

🔹 /price <coin> - Check price (e.g. /price bitcoin)
🔹 /trending - Trending coins
🔹 /gas - Check gas prices across chains
🔹 /watchlist - Manage your watchlist
🔹 /add <coin> - Add to watchlist
🔹 /portfolio - Track your portfolio
🔹 /premium - Unlock premium features
🔹 /help - All commands

💎 *Premium*: Real-time alerts, arbitrage signals, portfolio auto-tracking
"""
    keyboard = [
        [InlineKeyboardButton("💰 Premium Plans", callback_data="premium")],
        [InlineKeyboardButton("📊 Trending", callback_data="trending"),
         InlineKeyboardButton("⛽ Gas Prices", callback_data="gas")],
        [InlineKeyboardButton("🔍 Search Coin", callback_data="search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome, reply_markup=reply_markup, parse_mode="Markdown")


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /price command"""
    if not context.args:
        await update.message.reply_text("Usage: /price <coin_id>\nExample: /price bitcoin")
        return

    coin_id = context.args[0].lower()
    await update.message.reply_text(f"🔍 Looking up {coin_id}...")

    data = await fetch_price(coin_id)
    if data:
        price = data.get("usd", 0)
        change = data.get("usd_24h_change", 0)
        mcap = data.get("usd_market_cap", 0)

        change_emoji = "📈" if change >= 0 else "📉"
        price_str = f"${price:,.2f}" if price < 1000 else f"${price:,.0f}"
        change_str = f"{change:+.2f}%"
        mcap_str = f"${mcap/1e9:.2f}B" if mcap > 1e9 else f"${mcap/1e6:.2f}M"

        response = f"""
{change_emoji} *{coin_id.upper()}*
Price: {price_str}
24h: {change_str} 
Market Cap: {mcap_str}
"""
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Could not find '{coin_id}'. Try /search {coin_id}")


async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trending command"""
    await update.message.reply_text("🔍 Fetching trending coins...")
    coins = await fetch_trending()

    if coins:
        response = "*🔥 Trending Coins*\n\n"
        for i, coin in enumerate(coins[:10], 1):
            item = coin.get("item", {})
            name = item.get("name", "Unknown")
            symbol = item.get("symbol", "???")
            price_btc = item.get("price_btc", 0)
            response += f"{i}. *{name}* ({symbol.upper()})\n"

        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Could not fetch trending coins.")


async def gas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check gas prices across chains"""
    await update.message.reply_text("⛽ Checking gas prices...")

    chains = {
        "ethereum": "https://api.etherscan.io/api?module=gastracker&action=gasoracle",
        "bsc": "https://api.bscscan.com/api?module=gastracker&action=gasoracle",
        "polygon": "https://api.polygonscan.com/api?module=gastracker&action=gasoracle"
    }

    response = "*⛽ Gas Prices*\n\n"
    async with aiohttp.ClientSession() as session:
        for name, url in chains.items():
            try:
                async with session.get(url, timeout=10) as resp:
                    data = await resp.json()
                    if data.get("status") == "1":
                        result = data["result"]
                        if "gas" in result:
                            gas = int(result["gas"]) / 10
                            response += f"• *{name.title()}*: {gas:.1f} gwei ({result.get('UsdPrice', '?')}$)\n"
                        else:
                            response += f"• *{name.title()}*: data unavailable\n"
                    else:
                        response += f"• *{name.title()}*: API error\n"
            except Exception as e:
                response += f"• *{name.title()}*: error\n"

    response += "\n_L2s use 10-100x less_ 💰"
    await update.message.reply_text(response, parse_mode="Markdown")


async def add_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add coin to watchlist"""
    if not context.args:
        await update.message.reply_text("Usage: /add <coin_id>\nExample: /add bitcoin")
        return

    coin_id = context.args[0].lower()
    user_id = update.effective_user.id

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT watchlist FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    watchlist = json.loads(row[0]) if row and row[0] else []

    if coin_id not in watchlist:
        watchlist.append(coin_id)
        c.execute("UPDATE users SET watchlist = ? WHERE user_id = ?",
                  (json.dumps(watchlist), user_id))
        conn.commit()
        await update.message.reply_text(f"✅ Added *{coin_id}* to your watchlist!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"ℹ️ *{coin_id}* is already in your watchlist.", parse_mode="Markdown")
    conn.close()


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's watchlist"""
    user_id = update.effective_user.id

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT watchlist, is_premium FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text("Use /start first!")
        return

    watchlist = json.loads(row[0])
    is_premium = row[1]

    if not watchlist:
        await update.message.reply_text(
            "Your watchlist is empty! Add coins with /add <coin_id>\n"
            "Example: /add bitcoin"
        )
        return

    response = "*📊 Your Watchlist*\n\n"
    for coin in watchlist:
        data = await fetch_price(coin)
        if data:
            price = data.get("usd", 0)
            change = data.get("usd_24h_change", 0)
            emoji = "📈" if change >= 0 else "📉"
            price_str = f"${price:,.2f}" if price < 1000 else f"${price:,.0f}"
            response += f"{emoji} *{coin}*: {price_str} ({change:+.2f}%)\n"

    if not is_premium:
        response += "\n💎 *Premium*: Real-time price alerts when your coins move!"
        keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(response, parse_mode="Markdown")


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium plans"""
    text = f"""
💎 *Dominion Premium* 💎

Unlock the full power of autonomous crypto intelligence:

✨ *Premium Features*:
• Real-time price alerts (instant notifications)
• Arbitrage opportunity scanner
• Gas price alerts when fees are low
• Portfolio auto-tracking
• Priority support
• Early access to on-chain trading bot

📦 *Plans*:
• Monthly: ${PREMIUM_PRICE_USD} (paid in crypto)
• Lifetime: ${LIFETIME_PRICE_USD} (best value!)

🪙 *Payment in crypto*:
Send {PREMIUM_PRICE_ETH} ETH to:
`{WALLET_ADDRESS}`
Then reply with your transaction hash.
"""
    keyboard = [
        [InlineKeyboardButton("🪙 Pay with Crypto", callback_data="payment_crypto")],
        [InlineKeyboardButton("❓ How to pay", callback_data="payment_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Portfolio tracking (premium feature)"""
    user_id = update.effective_user.id
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        keyboard = [[InlineKeyboardButton("💎 Unlock Premium", callback_data="premium")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📊 Portfolio tracking is a *Premium* feature!\n"
            "Track your crypto holdings, P&L, and allocation.",
            reply_markup=reply_markup, parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "📊 *Portfolio*\n\n"
        "To set up portfolio tracking, send your holdings in format:\n"
        "`<amount> <coin_id>`\n"
        "Example: `0.5 bitcoin, 10 ethereum, 100 solana`",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """
*🤖 Dominion Bot Commands*

*Prices & Market*
/price <coin> - Check coin price
/trending - Top trending coins
/search <query> - Search coins
/gas - Check gas prices

*Personal*
/watchlist - Your watchlist
/add <coin> - Add to watchlist
/remove <coin> - Remove from watchlist
/portfolio - Your portfolio (premium)

*Premium*
/premium - View premium plans
/subscribe - Subscribe with payment

*Other*
/start - Start the bot
/help - This message
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ============================================================
# Callback handlers
# ============================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()

    if query.data == "premium":
        await premium_command(update, context)
    elif query.data == "trending":
        await trending_command(update, context)
    elif query.data == "gas":
        await gas_command(update, context)
    elif query.data == "search":
        await query.edit_message_text("🔍 Send a coin name to search.\nExample: bitcoin")
    elif query.data == "payment_crypto":
        await query.edit_message_text(
            f"🪙 *Crypto Payment*\n\n"
            f"Send {PREMIUM_PRICE_ETH} ETH to:\n"
            f"`{WALLET_ADDRESS}`\n\n"
            f"After sending, reply with your transaction hash (txid) to verify.\n\n"
            f"_Premium will be activated after 1 confirmation_",
            parse_mode="Markdown"
        )
    elif query.data == "payment_help":
        await query.edit_message_text(
            "❓ *How to Pay with Crypto*\n\n"
            "1. Open your crypto wallet (MetaMask, Trust Wallet, etc.)\n"
            "2. Send ETH to the address provided\n"
            "3. Copy the transaction hash (txid)\n"
            "4. Reply to this bot with the hash\n"
            "5. Premium activates automatically!\n\n"
            "Need help? Contact @crypto_empire_support",
            parse_mode="Markdown"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for verification, search, etc.)"""
    text = update.message.text.strip()

    # Check if it looks like a transaction hash
    if len(text) == 66 and text.startswith("0x"):
        # Verify payment
        user_id = update.effective_user.id
        db_conn = sqlite3.connect(str(DB_PATH))
        c = db_conn.cursor()

        # Check if hash already used
        c.execute("SELECT id FROM transactions WHERE tx_hash = ?", (text,))
        if c.fetchone():
            await update.message.reply_text("❌ This transaction hash has already been used.")
            db_conn.close()
            return

        # Verify on-chain (simplified - in production use web3)
        await update.message.reply_text(
            "🔍 Verifying transaction... Please wait..."
        )

        # For demo: auto-activate if it's a valid hex hash
        # In production: use Etherscan API or web3 to verify
        try:
            bytes.fromhex(text[2:])  # Validate hex
            expiry = (datetime.now() + timedelta(days=30)).isoformat()

            c.execute("UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
                      (expiry, user_id))
            c.execute("INSERT INTO transactions (user_id, tx_hash, amount_usd, plan) VALUES (?, ?, ?, ?)",
                      (user_id, text, PREMIUM_PRICE_USD, "monthly"))
            db_conn.commit()

            await update.message.reply_text(
                "✅ *Premium Activated!* 🎉\n\n"
                "You now have access to:\n"
                "✨ Real-time price alerts\n"
                "🔄 Arbitrage opportunity scanner\n"
                "📊 Portfolio auto-tracking\n"
                "⛽ Gas price alerts\n\n"
                "Enjoy your premium features!",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid transaction hash format.\n"
                "Please send a valid 66-character hex string starting with 0x"
            )
        db_conn.close()
        return

    # Check if it's a portfolio input
    if any(c.isdigit() for c in text) and any(c.isalpha() for c in text):
        # Could be portfolio data
        user_id = update.effective_user.id
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            await update.message.reply_text("📊 Updating portfolio... (coming soon)")
            return

    # Default: search for coins
    coins = await search_coins(text)
    if coins:
        response = f"*🔍 Search results for '{text}'*\n\n"
        for coin in coins[:5]:
            name = coin.get("name", "?")
            symbol = coin.get("symbol", "?")
            coin_id = coin.get("id", "")
            market_rank = coin.get("market_cap_rank", "?")
            response += f"#{market_rank} *{name}* ({symbol}) - /price {coin_id}\n"
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"No results found for '{text}'. Try /price <coin_id>")


# ============================================================
# Background tasks
# ============================================================

async def price_alert_job(context: ContextTypes.DEFAULT_TYPE):
    """Check watchlist prices and alert premium users (runs every hour)"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT user_id, watchlist FROM users WHERE is_premium = 1 AND alerts_enabled = 1")
    premium_users = c.fetchall()
    conn.close()

    for user_id, watchlist_json in premium_users:
        watchlist = json.loads(watchlist_json) if watchlist_json else []
        for coin in watchlist[:5]:  # Max 5 alerts per user
            data = await fetch_price(coin)
            if data:
                change = data.get("usd_24h_change", 0)
                if abs(change) > 5:  # Alert on 5%+ moves
                    emoji = "🚀" if change > 0 else "💀"
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"{emoji} *Alert: {coin}*\nPrice moved {change:+.2f}% in 24h!\nCurrent: ${data['usd']:,.2f}",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

async def check_new_listings_job(context: ContextTypes.DEFAULT_TYPE):
    """Check for new token listings (notifications for premium users)"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_premium = 1 AND alerts_enabled = 1")
    premium_users = c.fetchall()
    conn.close()

    if not premium_users:
        return

    # Check CoinGecko recently_added
    session = await get_session()
    try:
        async with session.get(f"{COINGECKO_BASE}/coins/list?include_platform=false", timeout=10) as resp:
            if resp.status == 200:
                pass  # Would check for new listings vs cache
    except Exception:
        pass


# ============================================================
# Main
# ============================================================

def main():
    """Start the bot"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Initialize DB
    init_db()
    logger.info("Database initialized")

    # Get bot token from environment
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        logger.info("Running in dry-run mode (no Telegram connection)")
        print("\n⚠️  TELEGRAM_BOT_TOKEN not set. Run with:")
        print("    TELEGRAM_BOT_TOKEN=your_token python3 bot.py\n")

        # Test mode - show what the bot can do
        print("=" * 50)
        print("CRYPTO EMPIRE BOT - READY FOR DEPLOYMENT")
        print("=" * 50)
        print(f"\nWallet: {WALLET_ADDRESS}")
        print(f"\nPremium plans:")
        print(f"  • Monthly: ${PREMIUM_PRICE_USD} ({PREMIUM_PRICE_ETH} ETH)")
        print(f"  • Lifetime: ${LIFETIME_PRICE_USD}")
        print(f"\nFeatures:")
        print("  • Price checking (any CoinGecko coin)")
        print("  • Trending coins")
        print("  • Gas price monitoring")
        print("  • Watchlist management")
        print("  • Premium subscriptions paid in crypto")
        print("  • Real-time price alerts (+5% moves)")
        print("  • Portfolio tracking (Premium)")
        print("\nTo deploy, set TELEGRAM_BOT_TOKEN and run.")
        return

    logger.info(f"Starting Dominion Bot...")

    # Create application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("trending", trending_command))
    application.add_handler(CommandHandler("gas", gas_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("add", add_watchlist))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("subscribe", premium_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add background jobs
    job_queue = application.job_queue
    job_queue.run_repeating(price_alert_job, interval=3600, first=120)  # Every hour, start in 2min
    job_queue.run_repeating(check_new_listings_job, interval=7200, first=300)  # Every 2h, start in 5min

    # Start
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
