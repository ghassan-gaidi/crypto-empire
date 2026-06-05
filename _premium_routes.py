


@app.route("/premium")
def premium_page():
    """Premium subscription page"""
    customer = request.args.get("customer_id", "")
    customer_email = request.args.get("email", "")
    status = ""
    if customer:
        status = "active" if _is_premium(customer) else "inactive"
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Premium — Crypto Empire</title>
    <meta name="description" content="Unlock premium features: advanced whale alerts, priority price alerts, and exclusive market data.">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">Premium</div>
                    <div class="site-sub">Unlock the full empire</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="/">Dashboard</a>
                <a href="/docs">API</a>
                <a href="/api-keys">Keys</a>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot"></span> PREMIUM TIER</span>
            <span id="live-clock">--</span>
        </div>

        <div class="post" style="margin-bottom:16px;">
            <h3 style="font-size:12px;color:var(--white);text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">FREE TIER</h3>
            <p style="font-size:10px;color:var(--text-dim);line-height:1.6;">
                <span style="color:var(--green);">&#10003;</span> Live crypto prices & charts<br>
                <span style="color:var(--green);">&#10003;</span> Gas tracker (ETH/BSC/Polygon)<br>
                <span style="color:var(--green);">&#10003;</span> Whale tracker (web page)<br>
                <span style="color:var(--green);">&#10003;</span> Trending coins<br>
                <span style="color:var(--text-dim);">&#10007;</span> <span style="color:var(--text-dim);">Telegram whale alerts</span><br>
                <span style="color:var(--text-dim);">&#10007;</span> <span style="color:var(--text-dim);">Priority price alerts</span><br>
                <span style="color:var(--text-dim);">&#10007;</span> <span style="color:var(--text-dim);">Premium indicators</span>
            </p>
        </div>

        <div class="prem-box" style="text-align:left;border-color:var(--white);">
            <h3 style="font-size:12px;margin-bottom:12px;color:var(--green);">PREMIUM TIER -- $9.99 / month</h3>
            <p style="font-size:10px;color:var(--text-dim);line-height:1.6;">
                <span style="color:var(--green);">&#10003;</span> <strong style="color:var(--white);">Telegram whale alerts</strong> -- real-time push on every $100K+ move<br>
                <span style="color:var(--green);">&#10003;</span> <strong style="color:var(--white);">Priority price alerts</strong> -- instant notifications on key thresholds<br>
                <span style="color:var(--green);">&#10003;</span> <strong style="color:var(--white);">Premium sentiment indicators</strong> -- buy/sell signals<br>
                <span style="color:var(--green);">&#10003;</span> <strong style="color:var(--white);">Ad-free</strong> across all pages<br>
                <span style="color:var(--green);">&#10003;</span> Support development -- help keep the empire running
            </p>
        </div>
""" + ("{% if customer_status == \"active\" %}"
"""
        <div style="margin-top:16px;padding:12px;border:1px solid var(--green);text-align:center;">
            <span style="color:var(--green);font-size:10px;text-transform:uppercase;letter-spacing:2px;">&#10003; PREMIUM ACTIVE</span>
        </div>
""" + "{% else %}"
"""
        <div style="margin-top:16px;display:flex;gap:8px;">
            <a href=\"""" + POLAR_CHECKOUT_URL + """\" target="_blank" style="flex:1;display:block;padding:10px;background:var(--white);color:var(--bg);text-align:center;text-decoration:none;font-size:10px;letter-spacing:1px;text-transform:uppercase;border-radius:0;">
                Subscribe $9.99/mo
            </a>
        </div>
        <p style="font-size:9px;color:var(--text-dim);text-align:center;margin-top:8px;">
            Powered by Polar.sh &bull; $9.99/month &bull; Cancel anytime
        </p>
""" + "{% endif %}")
+ """
        <div class="bnav" style="margin-top:16px;">
            <a href="/">&#8592; Dashboard</a>
        </div>
    </div>
    <script>
    function updateClock(){
        var d=new Date();
        document.getElementById('live-clock').textContent=
            d.toLocaleTimeString('en-US',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'UTC'})+' UTC';
    }
    updateClock();setInterval(updateClock,1000);
    </script>
</body>
</html>""")


@app.route("/api/premium/check")
def api_premium_check():
    """Check premium status for a customer"""
    customer = request.args.get("customer_id", "")
    if not customer:
        return jsonify({"premium": False, "error": "customer_id required"}), 400
    return jsonify({"premium": _is_premium(customer), "customer_id": customer})


@app.route("/api/premium/webhook", methods=["POST"])
def api_premium_webhook():
    """Receive Polar subscription webhooks"""
    data = request.get_json(silent=True) or {}
    event_type = data.get("type", "")

    # Only process subscription events
    if event_type in ("subscription.active", "subscription.updated", "subscription.canceled", "subscription.revoked"):
        sub_data = data.get("data", {})
        customer_id = sub_data.get("customer_id") or sub_data.get("customer", {}).get("id", "")
        status = sub_data.get("status", "")

        if customer_id:
            subs = _load_subs()
            if customer_id not in subs:
                subs[customer_id] = {}
            subs[customer_id].update({
                "status": status,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "subscription_id": sub_data.get("id", ""),
                "product_id": sub_data.get("product_id", ""),
                "current_period_end": sub_data.get("current_period_end", ""),
            })
            _save_subs(subs)

            # Send TG notification about new subscriber
            if event_type == "subscription.active":
                try:
                    from telegram_bot import send_telegram
                    send_telegram(f"🎉 *New Premium Subscriber!*\nCustomer: `{customer_id}`\nStatus: `{status}`")
                except:
                    pass

    return jsonify({"ok": True})


@app.route("/api/premium/subscribers")
def api_premium_subscribers():
    """List all premium subscribers (admin only)"""
    key = request.args.get("key", "")
    if key != os.environ.get("WHALE_REFRESH_SECRET", ""):
        return jsonify({"error": "unauthorized"}), 403
    subs = _load_subs()
    active = {k: v for k, v in subs.items() if v.get("status") in ("active", "trialing")}
    return jsonify({"total": len(subs), "active": len(active), "subscribers": dict(list(subs.items())[:50])})

