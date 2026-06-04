#!/usr/bin/env python3
"""
One-time script to register the Telegram webhook URL.
Usage: python setup_webhook.py [url]
  Default: https://crypto-empire-ten.vercel.app/telegram/webhook
"""
import os
import sys
import requests

# Read token from same source as telegram_bot.py
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or ""
if not TELEGRAM_TOKEN:
    token_path = os.path.join(os.path.dirname(__file__), ".telegram_token")
    if os.path.exists(token_path):
        TELEGRAM_TOKEN = open(token_path).read().strip()

if not TELEGRAM_TOKEN:
    print("ERROR: No TELEGRAM_TOKEN found. Set env var or save to .telegram_token")
    sys.exit(1)

WEBHOOK_URL = sys.argv[1] if len(sys.argv) > 1 else "https://crypto-empire-ten.vercel.app/telegram/webhook"

api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Set webhook
r = requests.post(f"{api}/setWebhook", json={"url": WEBHOOK_URL}, timeout=10)
print("setWebhook:", r.json())

# Verify
r2 = requests.get(f"{api}/getWebhookInfo", timeout=10)
info = r2.json()
print("\ngetWebhookInfo:")
print(f"  URL:           {info.get('result', {}).get('url', 'N/A')}")
print(f"  Pending:       {info.get('result', {}).get('pending_update_count', 'N/A')}")
print(f"  Last error:    {info.get('result', {}).get('last_error_message', 'none')}")
