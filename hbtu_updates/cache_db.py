import json
import os
import sqlite3
import time
from typing import Any

DB_PATH = "Temp/hbtu_cache.db"


def _get_connection() -> sqlite3.Connection:
    os.makedirs("Temp", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS page_cache (
            page_key TEXT PRIMARY KEY,
            fetched_at REAL NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_links (
            link TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            source TEXT NOT NULL,
            first_seen_at REAL NOT NULL,
            last_seen_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get_cached_links(page_key: str, max_age_seconds: int) -> list[dict[str, Any]] | None:
    now = time.time()
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT fetched_at, payload FROM page_cache WHERE page_key = ?",
            (page_key,),
        ).fetchone()
    if not row:
        return None
    fetched_at, payload = row
    if (now - fetched_at) > max_age_seconds:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return parsed


def set_cached_links(page_key: str, links: list[dict[str, Any]]) -> None:
    payload = json.dumps(links, ensure_ascii=False)
    now = time.time()
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO page_cache (page_key, fetched_at, payload)
            VALUES (?, ?, ?)
            ON CONFLICT(page_key) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                payload = excluded.payload
            """,
            (page_key, now, payload),
        )
        conn.commit()


def filter_new_links(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = time.time()
    new_items: list[dict[str, Any]] = []
    with _get_connection() as conn:
        for item in items:
            link = item.get("link")
            text = item.get("text")
            source = item.get("source", "Unknown")
            if not isinstance(link, str) or not link:
                continue
            if not isinstance(text, str) or not text:
                continue

            existing = conn.execute(
                "SELECT link FROM seen_links WHERE link = ?",
                (link,),
            ).fetchone()
            if not existing:
                new_items.append(item)
                conn.execute(
                    """
                    INSERT INTO seen_links (link, text, source, first_seen_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (link, text, source, now, now),
                )
            else:
                conn.execute(
                    """
                    UPDATE seen_links
                    SET text = ?, source = ?, last_seen_at = ?
                    WHERE link = ?
                    """,
                    (text, source, now, link),
                )
        conn.commit()
    return new_items
