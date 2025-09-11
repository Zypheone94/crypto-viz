import os
import time
import signal
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import threading
import asyncio
import requests
from urllib.parse import urlparse
from twisted.internet import reactor
from bs4 import BeautifulSoup
from scrapers.run_spiders import setup_crawler
from scrapers.spiders.coindesk_spider import CoinDeskSpider
from scrapers.spiders.coingecko_spider import CoinGeckoSpider

load_dotenv()
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL"))
SOURCES = os.getenv("SOURCES")
DATA_PATH = os.getenv("DATA_PATH")
SCRAPER_PORT = int(os.getenv("SCRAPER_PORT"))

start_time = time.time()
last_write_at = None
shutdown_event = threading.Event()

# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the crawler in the background
    task = asyncio.create_task(run_spider_job())
    
    # Start the reactor in a separate thread if it's not running
    if not reactor.running:
        thread = threading.Thread(target=reactor.run, args=(False,))
        thread.start()
    
    yield
    
    # Cleanup
    shutdown_event.set()
    reactor.callFromThread(reactor.stop)
    await task

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Initialize the crawler runner
runner = setup_crawler(DATA_PATH)

def scrape_website(url):
	try:
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5',
			'Connection': 'keep-alive',
		}
		resp = requests.get(url, timeout=30, headers=headers)
		resp.raise_for_status()
		soup = BeautifulSoup(resp.text, 'html.parser')
		
		data = {
			'url': url,
			'source': urlparse(url).netloc,
			'title': soup.title.string.strip() if soup.title else 'No title found',
			'timestamp': datetime.now().isoformat(),
			'scrape_date': datetime.now().strftime('%Y-%m-%d'),
			'status': 'success'
		}
		
			# Add source-specific parsing
		if 'coingecko.com' in url:
			try:
				# Get crypto prices from CoinGecko
				data['crypto_data'] = []
				
				# Try different potential selectors for cryptocurrency rows
				selectors = [
					'div[data-test-id="gecko-table-cryptocurrency"] tbody tr',  # New selector
					'div.coin-table div[data-target="currencies.contentBox"] > div',  # Alternative
					'table.table-coins tr[data-id]'  # Legacy
				]
				
				for selector in selectors:
					crypto_rows = soup.select(selector)
					if crypto_rows:
						for row in crypto_rows[:10]:
							try:
								# Try different selectors for name and price
								name = (
									row.select_one('[data-test-id="coin-name"]') or
									row.select_one('.coin-name') or
									row.select_one('a[href*="/en/coins/"]')
								)
								
								price = (
									row.select_one('[data-test-id="price"]') or
									row.select_one('.td-price span') or
									row.select_one('span[data-price]')
								)
								
								if name and price:
									data['crypto_data'].append({
										'name': name.text.strip(),
										'price': price.text.strip(),
										'selector_used': selector
									})
							except Exception as e:
								print(f"Error parsing row: {e}")
						
						if data['crypto_data']:
							break  # Stop if we found data with current selector
				
				if not data['crypto_data']:
					# Save HTML for debugging
					data['debug_html'] = str(soup.select('body')[0])[:500] if soup.select('body') else "No body found"
					
			except Exception as e:
				data['crypto_data_error'] = str(e)
				
		elif 'coindesk.com' in url:
			try:
				data['news_data'] = []
				
				# Try different selectors for articles
				article_selectors = [
					'div.article-card',
					'article',
					'div[data-type="article"]',
					'div.story-card'
				]
				
				for selector in article_selectors:
					articles = soup.select(selector)
					if articles:
						for article in articles[:10]:
							article_data = {}
							
							# Try different link selectors
							link_selectors = [
								'a[href*="/markets/"]',
								'a[href*="/business/"]',
								'a[href*="/tech/"]',
								'a[href*="/policy/"]',
								'a.story-card-link',
								'a.article-link'
							]
							
							link_elem = None
							for link_selector in link_selectors:
								link_elem = article.select_one(link_selector)
								if link_elem:
									break
							
							if link_elem and 'href' in link_elem.attrs:
								article_url = link_elem['href']
								if not article_url.startswith('http'):
									article_url = 'https://www.coindesk.com' + article_url
								
								try:
									article_resp = requests.get(article_url, timeout=30, headers=headers)
									article_resp.raise_for_status()
									article_soup = BeautifulSoup(article_resp.text, 'html.parser')
									
									# Get article title - try multiple selectors
									title_selectors = ['h1.article-header', 'h1.heading', 'h1']
									for title_selector in title_selectors:
										title_elem = article_soup.select_one(title_selector)
										if title_elem:
											article_data['title'] = title_elem.text.strip()
											break
									
									# Get article date - try multiple selectors
									date_selectors = [
										'time[datetime]',
										'span.article-date',
										'div.date-posted time'
									]
									for date_selector in date_selectors:
										date_elem = article_soup.select_one(date_selector)
										if date_elem:
											article_data['date'] = date_elem.get('datetime', '') or date_elem.text.strip()
											break
									
									# Get article content
									content_selectors = [
										'div.article-content',
										'div.article-body',
										'article'
									]
									
									for content_selector in content_selectors:
										content_elem = article_soup.select_one(content_selector)
										if content_elem:
											paragraphs = content_elem.select('p')[:3]
											if paragraphs:
												article_data['content'] = '\n'.join([p.text.strip() for p in paragraphs])
												break
									
									article_data['url'] = article_url
									article_data['status'] = 'success'
									
									# Debug info
									if not article_data.get('title') or not article_data.get('content'):
										article_data['debug_info'] = {
											'found_selectors': {
												'title': bool(article_data.get('title')),
												'date': bool(article_data.get('date')),
												'content': bool(article_data.get('content'))
											}
										}
									
									# Add a small delay between article requests
									time.sleep(2)
									
								except Exception as e:
									article_data['status'] = 'error'
									article_data['error'] = str(e)
									article_data['url'] = article_url
							
							if article_data:
								data['news_data'].append(article_data)
						
						if data['news_data']:
							break  # Stop if we found articles with current selector
				
				if not data['news_data']:
					# Save sample HTML for debugging
					data['debug_html'] = str(soup.select('body')[0])[:500] if soup.select('body') else "No body found"
					
			except Exception as e:
				data['news_data_error'] = str(e)
				
		return data
	except Exception as e:
		return {
			'url': url,
			'source': urlparse(url).netloc,
			'timestamp': datetime.now().isoformat(),
			'scrape_date': datetime.now().strftime('%Y-%m-%d'),
			'status': 'error',
			'error': str(e)
		}

async def run_spider_job():
    while not shutdown_event.is_set():
        try:
            # Schedule both spiders
            deferred = runner.crawl(CoinDeskSpider)
            deferred.addCallback(lambda _: setattr(globals(), 'last_write_at', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
            deferred = runner.crawl(CoinGeckoSpider)
            deferred.addCallback(lambda _: setattr(globals(), 'last_write_at', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
            
            # Wait for FETCH_INTERVAL before next crawl
            await asyncio.sleep(FETCH_INTERVAL)
        except Exception as e:
            print(f"Error in spider job: {e}")
            await asyncio.sleep(FETCH_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the crawler in the background
    task = asyncio.create_task(run_spider_job())
    
    # Start the reactor in a separate thread if it's not running
    if not reactor.running:
        thread = threading.Thread(target=reactor.run, args=(False,))
        thread.start()
    
    yield
    
    # Cleanup
    shutdown_event.set()
    reactor.callFromThread(reactor.stop)
    await task

# Add lifespan to FastAPI app
app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
	uptime = int(time.time() - start_time)
	return JSONResponse({
		"status": "ok",
		"last_write_at": last_write_at,
		"uptime": uptime
	})

def run_server():
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=SCRAPER_PORT)

def handle_sigterm(signum, frame):
	shutdown_event.set()

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SCRAPER_PORT)
