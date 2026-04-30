from datetime import datetime
from app.db.clickhouse import get_clickhouse

async def log_click(short_code: str, ip: str, referrer: str):
    try:
        # IP ni anonymize qilamiz — faqat /24 saqlaymiz
        # 192.168.1.100 → 192.168.1
        ip_prefix = ".".join(ip.split(".")[:3]) if ip else "unknown"

        # Referrer domenini olamiz
        # https://google.com/search?q=... → google.com
        if referrer and "://" in referrer:
            referrer_domain = referrer.split("://")[1].split("/")[0]
        elif referrer:
            referrer_domain = referrer
        else:
            referrer_domain = "direct"

        client = get_clickhouse()
        client.insert(
            "poc014.click_events",
            [[datetime.now(), short_code, "UZ", referrer_domain, ip_prefix]],
            column_names=["event_time", "short_code", "country_code", "referrer", "ip_prefix"]
        )
    except Exception as e:
        # Analytics xatosi redirect ni to'xtatmasin
        print(f"Analytics error: {e}")
