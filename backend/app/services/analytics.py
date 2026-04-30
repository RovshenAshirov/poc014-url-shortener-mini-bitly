import asyncio
from datetime import datetime
from app.db.clickhouse import get_clickhouse

_queue: asyncio.Queue = asyncio.Queue(maxsize=50_000)


def enqueue_click(short_code: str, ip: str, referrer: str) -> None:
    """Non-blocking; silently drops under extreme load."""
    try:
        _queue.put_nowait((datetime.now(), short_code, ip, referrer))
    except asyncio.QueueFull:
        pass


def _batch_insert(rows: list) -> None:
    processed = []
    for (event_time, short_code, ip, referrer) in rows:
        # IP ni anonymize qilamiz — faqat /24 saqlaymiz
        # 192.168.1.100 → 192.168.1
        ip_prefix = ".".join(ip.split(".")[:3]) if ip else "unknown"

        # Referrer domenini olamiz
        # https://google.com/search?q=... → google.com
        if referrer and "://" in referrer:
            domain = referrer.split("://")[1].split("/")[0]
        elif referrer:
            domain = referrer
        else:
            domain = "direct"
        processed.append([event_time, short_code, "UZ", domain, ip_prefix])
    get_clickhouse().insert(
        "poc014.click_events",
        processed,
        column_names=["event_time", "short_code", "country_code", "referrer", "ip_prefix"],
    )


async def flush_worker() -> None:
    """Single background coroutine — drains queue in batches, never blocks redirect path."""
    while True:
        await asyncio.sleep(1)
        if _queue.empty():
            continue
        batch = []
        try:
            while len(batch) < 1000:
                batch.append(_queue.get_nowait())
        except asyncio.QueueEmpty:
            pass
        if batch:
            try:
                await asyncio.to_thread(_batch_insert, batch)
            except Exception as e:
                print(f"ClickHouse batch insert error: {e}")
