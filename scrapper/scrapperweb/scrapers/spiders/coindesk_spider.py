from scrapy import Spider, Request
from datetime import datetime, timezone
from urllib.parse import urljoin
from pathlib import Path
import sys
import re

sys.path.append(str(Path(__file__).parent.parent.parent))

class CoinDeskSpider(Spider):
    name = 'coindesk'
    allowed_domains = ['coindesk.com']
    start_urls = [
        'https://www.coindesk.com',
        'https://www.coindesk.com/markets/',
        'https://www.coindesk.com/business/',
        'https://www.coindesk.com/tech/',
        'https://www.coindesk.com/policy/'
    ]

    custom_settings = {
        'USER_AGENT': 'crypto-viz-scraper/1.0',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'LOG_LEVEL': 'DEBUG'
    }

    def parse(self, response):
        self.logger.info(f"Visiting page: {response.url}")

        links = response.css('a::attr(href)').getall()
        article_links = set()

        for link in links:
            full_link = urljoin(response.url, link)
            if link and 'coindesk.com' in full_link:
                if any(x in link for x in ['/markets/', '/business/', '/tech/', '/policy/', '/consensus/', '/coindesk-indices/', '/daybook-us/']):
                    if '/tag/' not in link:
                        article_links.add(full_link)

        self.logger.info(f"Found {len(article_links)} article links on {response.url}")

        # Limit to first 20 links for testing
        for link in list(article_links)[:20]:
            yield Request(link, callback=self.parse_article, meta={'source_page': response.url})

    def parse_article(self, response):
        self.logger.info(f"Scraping article: {response.url}")
        try:
            # Extract title
            title = response.css(
                'h1::text, h1.heading::text, h1.article-header::text, title::text'
            ).get(default='').strip()

            # Extract published date
            article_date = response.css(
                'meta[property="article:published_time"]::attr(content)'
            ).get()

            if not article_date:
                article_date = response.css(
                    'time[datetime]::attr(datetime), '
                    'span.article-date time::attr(datetime), '
                    'div.date-posted time::attr(datetime)'
                ).get()

            if not article_date:
                m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', response.url)
                if m:
                    article_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00Z"

            if not article_date:
                article_date = datetime.now(timezone.utc).isoformat()

            # Normalize to ISO8601 UTC
            try:
                published_at = datetime.fromisoformat(article_date.replace("Z", "+00:00")).isoformat()
            except Exception:
                published_at = article_date

            # Extract content and author
            content = response.css(
                'div.article-content p::text, div.article-body p::text, article p::text'
            ).getall()
            author = response.css(
                'span.author-name::text, div.author a::text, span.byline::text'
            ).get(default='').strip()

            article_data = {
                'id': f"coindesk_{abs(hash(response.url))}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                'source': 'coindesk',
                'type': 'news_article',
                'url': response.url,
                'title': title,
                'author': author,
                'published_at': published_at,
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'content': '\n'.join(content[:10]) if content else '',
            }

            self.logger.info(f"Scraped article: {title}")
            yield article_data

        except Exception as e:
            self.logger.error(f'Error parsing article {response.url}: {e}')
            yield {
                'id': f"coindesk_error_{datetime.now().strftime("%Y%m%d_%H%M%S")}",
                'source': 'coindesk',
                'type': 'error',
                'url': response.url,
                'error': str(e),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
            }
