import time
from datetime import datetime, timezone
from typing import Iterable, List

import requests
from xml.etree import ElementTree as ET

from .models import ArticleModel


COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"


def _iso_to_dt(value: str) -> datetime:
    """Parse various date formats from RSS feeds"""
    if not value or not value.strip():
        return datetime.now(timezone.utc)
    
    value = value.strip()
    
    try:
        # Try ISO format first
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        pass
    
    try:
        # Try RFC822 format (common in RSS)
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass
    
    try:
        # Try dateutil for flexible parsing
        from dateutil import parser
        parsed = parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        pass
    
    # Fallback to current time
    return datetime.now(timezone.utc)


def fetch_rss(url: str, retries: int = 3, backoffs: List[int] = None, timeout: int = 20) -> str:
    if backoffs is None:
        backoffs = [5, 15, 60]
    attempt = 0
    while True:
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "crypto-viz/1.0"})
            resp.raise_for_status()
            return resp.text
        except Exception:
            if attempt >= retries - 1:
                raise
            time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
            attempt += 1


def parse_rss(xml_text: str, source: str) -> Iterable[ArticleModel]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall("item")

    now_utc = datetime.now(timezone.utc)
    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate") or item.find("published") or item.find("dc:date")
        desc_el = item.find("description") or item.find("content:encoded")

        if title_el is None or link_el is None:
            continue

        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        published_at = _iso_to_dt((pub_el.text or "").strip()) if pub_el is not None else now_utc
        content = (desc_el.text or "").strip() if desc_el is not None else None

        yield ArticleModel(
            id=ArticleModel.generate_id(link, title),
            title=title,
            url=link,
            source=source,
            published_at=published_at,
            fetched_at=now_utc,
            content=content,
        )


def fetch_and_parse_all() -> List[ArticleModel]:
    results: List[ArticleModel] = []
    for url, source in [
        (COINDESK_RSS, "coindesk"),
        (COINTELEGRAPH_RSS, "cointelegraph"),
    ]:
        xml_text = fetch_rss(url)
        results.extend(parse_rss(xml_text, source))
    return results


