import time
import sys
from datetime import datetime, timezone
from typing import Iterable, List
from pathlib import Path

import requests
from xml.etree import ElementTree as ET

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import after path setup
try:
    from ..models import ArticleModel
    from ..html_utils import strip_html_tags
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


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
    """
    Fetch RSS feed content with retries and timeout.
    
    Args:
        url: URL to fetch
        retries: Number of retry attempts
        backoffs: List of backoff times in seconds
        timeout: Request timeout in seconds
        
    Returns:
        str: RSS content text
        
    Raises:
        Exception: If all retry attempts fail
    """
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


def fetch_article_content(url: str, max_length: int = 10000) -> str:
    """Attempt to fetch the content of an article by visiting the URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find article content - common patterns
        content_selectors = [
            'article', 
            '.article-content', 
            '.post-content', 
            '.entry-content', 
            '.content', 
            '#content',
            'main'
        ]
        
        for selector in content_selectors:
            article_content = soup.select_one(selector)
            if article_content:
                # Extract text without scripts, styles...
                for script in article_content.find_all(['script', 'style']):
                    script.extract()
                text = article_content.get_text(separator=' ', strip=True)
                if len(text) > max_length:
                    text = text[:max_length] + '...'
                return text
        
        # Fallback to meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
            
        body = soup.body
        if body:
            text = body.get_text(separator=' ', strip=True)
            if len(text) > max_length:
                text = text[:max_length] + '...'
            return text
        
        return "Failed to extract content"
    except Exception as e:
        return f"Error fetching content: {str(e)}"

def parse_rss(xml_text: str, source: str) -> Iterable[ArticleModel]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall("item")

    now_utc = datetime.now(timezone.utc)
    
    content_ns = "{http://purl.org/rss/1.0/modules/content/}"
    dc_ns = "{http://purl.org/dc/elements/1.1/}"
    
    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate") or item.find("published") or item.find(f"{dc_ns}date")
        
        if title_el is None or link_el is None:
            continue

        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        published_at = _iso_to_dt((pub_el.text or "").strip()) if pub_el is not None else now_utc
        
        # Try multiple ways to find content from RSS
        content = None
        
        #content:encoded namespace
        encoded_el = item.find(f"{content_ns}encoded")
        if encoded_el is not None:
            content = ''.join(encoded_el.itertext()).strip()
        
        #description element
        if not content:
            desc_el = item.find("description")
            if desc_el is not None:
                content = ''.join(desc_el.itertext()).strip()
        
        #description
        if not content:
            dc_desc_el = item.find(f"{dc_ns}description")
            if dc_desc_el is not None:
                content = ''.join(dc_desc_el.itertext()).strip()

        if not content or len(content) < 100: 
            try:
                content = fetch_article_content(link)
            except Exception as e:
                print(f"Error fetching content for {link}: {e}")
                # Keep whatever content we found in the RSS
        
        # Strip HTML tags from content
        if content:
            content = strip_html_tags(content)

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


