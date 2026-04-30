import clickhouse_connect
from clickhouse_connect.driver.client import Client
from app.core.config import settings

_client: Client | None = None

def get_clickhouse() -> Client:
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
        )
    return _client

async def init_clickhouse():
    client = get_clickhouse()
    client.command(f"CREATE DATABASE IF NOT EXISTS {settings.CLICKHOUSE_DB}")
    client.command(f"""
        CREATE TABLE IF NOT EXISTS {settings.CLICKHOUSE_DB}.click_events (
            event_time   DateTime,
            short_code   String,
            country_code String,
            referrer     String,
            ip_prefix    String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(event_time)
        ORDER BY (short_code, event_time)
        TTL event_time + INTERVAL 1 YEAR
    """)

async def close_clickhouse():
    global _client
    if _client:
        _client.close()
        _client = None
