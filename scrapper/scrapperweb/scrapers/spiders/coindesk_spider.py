from scrapy import Spider, Request
from datetime import datetime, timezone

from urllib.parse import urljoin
from pathlib import Path
import sys
import re
import os
import requests

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

            # Extract author and published/updated date from text block if not found by CSS
            author = response.css(
                'span.author-name::text, div.author a::text, span.byline::text'
            ).get(default='').strip()
            if not author:
                # Try to extract from the byline text block
                byline_text = response.css('div.article-hero-byline, .byline, .article-byline').xpath('string(.)').get(default='')
                author_match = re.search(r'By ([^|\n]+)', byline_text)
                if author_match:
                    author = author_match.group(1).strip()

            # Extract published and updated date from text block
            published_at = None
            updated_at = None
            date_block = response.css('div.article-hero-byline, .byline, .article-byline').xpath('string(.)').get(default='')
            pub_match = re.search(r'Published\s+([A-Za-z]{3} \d{1,2}, \d{4},? \d{1,2}:\d{2}\s*[ap]\.m\.)', date_block)
            upd_match = re.search(r'Updated\s+([A-Za-z]{3} \d{1,2}, \d{4},? \d{1,2}:\d{2}\s*[ap]\.m\.)', date_block)
            def parse_date(date_str):
                try:
                    return datetime.strptime(date_str.replace('a.m.', 'AM').replace('p.m.', 'PM'), '%b %d, %Y, %I:%M %p').isoformat()
                except Exception:
                    return date_str
            if pub_match:
                published_at = parse_date(pub_match.group(1))
            if upd_match:
                updated_at = parse_date(upd_match.group(1))

            # Fallback to meta tags if not found
            if not published_at:
                article_date = response.css('meta[property="article:published_time"]::attr(content)').get()
                if not article_date:
                    article_date = response.css('time[datetime]::attr(datetime), span.article-date time::attr(datetime), div.date-posted time::attr(datetime)').get()
                if not article_date:
                    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', response.url)
                    if m:
                        article_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00Z"
                if not article_date:
                    article_date = datetime.now(timezone.utc).isoformat()
                try:
                    published_at = datetime.fromisoformat(article_date.replace("Z", "+00:00")).isoformat()
                except Exception:
                    published_at = article_date


            # Extract full content (all paragraphs, headers, and blockquotes)
            content_blocks = response.css('div.article-content, div.article-body, article')
            content = []
            for block in content_blocks:
                content += block.css('p::text, h2::text, h3::text, blockquote::text').getall()
            if not content:
                # fallback to all <p>, <h2>, <h3>, <blockquote> tags
                content = response.css('p::text, h2::text, h3::text, blockquote::text').getall()

            full_content = '\n'.join([c.strip() for c in content if c.strip()])


            # Paraphrase the article content using OpenAI API
            openai_api_key = os.getenv('openai_api_key')
            summary = ''
            if openai_api_key and full_content:
                try:
                    prompt = f"Paraphrase and summarize the following article in 3-5 sentences:\n{full_content[:4000]}"
                    response_api = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {openai_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": prompt}
                            ],
                            "max_tokens": 256,
                            "temperature": 0.7
                        },
                        timeout=20
                    )
                    if response_api.status_code == 200:
                        summary = response_api.json()['choices'][0]['message']['content'].strip()
                    else:
                        self.logger.warning(f"OpenAI API error: {response_api.text}")
                except Exception as e:
                    self.logger.warning(f"OpenAI API call failed: {e}")

            article_data = {
                'id': f"coindesk_{abs(hash(response.url))}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                'source': 'coindesk',
                'type': 'news_article',
                'url': response.url,
                'title': title,
                'author': author,
                'published_at': published_at,
                'updated_at': updated_at,
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'content': full_content,
                'summary': summary,
            }

            self.logger.info(f"Scraped article: {title}")
            yield article_data

        except Exception as e:
            self.logger.error(f'Error parsing article {response.url}: {e}')
            yield {
                'id': f"coindesk_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'source': 'coindesk',
                'type': 'error',
                'url': response.url,
                'error': str(e),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
            }
