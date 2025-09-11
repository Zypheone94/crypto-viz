from scrapy import Spider, Request
from datetime import datetime

class CoinDeskSpider(Spider):
    name = 'coindesk'
    allowed_domains = ['coindesk.com']
    start_urls = ['https://www.coindesk.com']
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1
    }

    def parse(self, response):
        # Extract all article links from the main page
        article_links = response.css('a[href*="/markets/"]::attr(href), a[href*="/business/"]::attr(href), a[href*="/tech/"]::attr(href)').getall()
        
        # Process each article
        for link in article_links[:10]:  # Limit to 10 articles
            if not link.startswith('http'):
                link = f'https://www.coindesk.com{link}'
            yield Request(link, callback=self.parse_article)

    def parse_article(self, response):
        yield {
            'source': 'coindesk',
            'url': response.url,
            'title': response.css('h1::text').get('').strip(),
            'date': response.css('time::attr(datetime)').get(),
            'content': '\n'.join(p.strip() for p in response.css('div.article-content p::text').getall()[:3]),
            'scrape_timestamp': datetime.now().isoformat()
        }
