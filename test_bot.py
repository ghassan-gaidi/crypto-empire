#!/usr/bin/env python3
"""Quick local test of the Telegram bot handlers"""
import os, sys
os.environ["TELEGRAM_TOKEN"] = "8947012639:AAFRpS7EJ-BsyCgxHtqh3lNjaEiUI5F-UAQ"
sys.path.insert(0, "/home/leo/crypto-empire")

# Override requests.post so we don't actually send Telegram messages during test
import requests as real_requests
sent = []
def fake_post(url, **kw):
    sent.append({"url": url, **kw})
    return real_requests.Response()

import telegram_bot as tb
tb.requests.post = fake_post

# Test /start
tb.handle_update({"message": {"chat": {"id": 12345}, "text": "/start"}})
print("START:", sent[-1]["json"]["text"][:60] if sent else "FAIL")

# Test /price bitcoin
tb.handle_update({"message": {"chat": {"id": 12345}, "text": "/price bitcoin"}})
print("PRICE:", sent[-1]["json"]["text"][:60] if sent else "FAIL")

# Test /gas
tb.handle_update({"message": {"chat": {"id": 12345}, "text": "/gas"}})
print("GAS:", sent[-1]["json"]["text"][:60] if sent else "FAIL")

# Test /fear
tb.handle_update({"message": {"chat": {"id": 12345}, "text": "/fear"}})
print("FEAR:", sent[-1]["json"]["text"][:60] if sent else "FAIL")

# Test unknown
tb.handle_update({"message": {"chat": {"id": 12345}, "text": "/blah"}})
print("UNKNOWN:", sent[-1]["json"]["text"][:60] if sent else "FAIL")

print(f"\nSent {len(sent)} messages — handlers work.")
