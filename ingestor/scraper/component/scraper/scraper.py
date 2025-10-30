import json
from datetime import datetime
from typing import Dict, Any, List

from bs4 import BeautifulSoup
from requests_html import HTMLSession

# Dictionnaire des parsers
SITE_PARSERS = {}

urls_to_parse = [
    "https://www.coingecko.com/?items=300",
    "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing",
    "https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products"
]

session = HTMLSession()

def site_parser(domain: str):
    def decorator(func):
        SITE_PARSERS[domain] = func
        return func

    return decorator

def clean_numbers(s: str) -> str:
    if not s:
        return None
    else:
        return s.replace("$", "").replace(",", "")


# ===================== PARSER COINGECKO =====================
@site_parser("coingecko.com")
def parse_coingecko(url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
    results = []
    table_rows = soup.select("table tbody tr")

    for tr in table_rows[:300]:
        name_tag = tr.select_one("a.tw-hidden") or tr.select_one("a.tw-flex")
        name = name_tag.get_text(strip=True) if name_tag else None
        symbol_tag = tr.select_one("div.tw-text-gray-500.dark\\:tw-text-moon-200")
        symbol = symbol_tag.get_text(strip=True) if symbol_tag else None

        price_tag = tr.select_one("span[data-price-target='price']")
        price = clean_numbers(price_tag.get_text(strip=True)) if price_tag else None

        # Market Cap → td à l’index 6
        tds = tr.select("span[data-price-target='price']")
        market_cap = None
        volume24 = None
        if len(tds) >= 2:
            volume24 = clean_numbers(tds[1].get_text(strip=True)) if len(tds) > 1 else None
            market_cap = clean_numbers(tds[2].get_text(strip=True)) if len(tds) > 2 else None

        results.append({
            "name": name,
            "symbol": symbol,
            "price": price,
            "market_cap": market_cap,
            "volume24": volume24,
            "published_at": "Published-at",
            "fetched_at": datetime.now().isoformat(),
            "coin_circulating": "coin_circulating",
            "url": url,
        })
    return results

@site_parser("coinmarketcap.com")
def parse_coinmarketcap(url: str,data: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    for item in data["data"]["cryptoCurrencyList"]:
        name = item["name"]
        symbol = item["symbol"]
        coin_circulating = clean_numbers(str(item["circulatingSupply"]))
        volume_24h = item["quotes"][0]["volume24h"]
        market_cap = clean_numbers(str(item["quotes"][0]["marketCap"]))
        price = clean_numbers(str(item["quotes"][0]["price"]))
        published_at = item["lastUpdated"]
        results.append({
            "name": name,
            "symbol": symbol,
            "price": price,
            "market_cap": market_cap,
            "volume_24h": volume_24h,
            "published_at": published_at,
            "fetched_at": datetime.now().isoformat(),
            "coin_circulating": coin_circulating,
            "url": url,
        })
    return results

@site_parser("binance.com")
def parse_binance(url: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:

    results = []
    STABLECOINS = ['USDT', 'FDUSD', 'BUSD', 'USDC', 'TUSD']

    unique_tokens = {}

    for item in data["data"]:
        quote = item['q']

        if quote not in STABLECOINS:
            continue

        symbol = item['b']
        price = float(item['c'])
        circulating = float(item['cs'])
        volume = float(item['qv'])
        market_cap = price * circulating

        if symbol not in unique_tokens or volume > float(unique_tokens[symbol]['volume_24h']):
            results.append({
                "name": item['an'],
                "symbol": symbol,
                "price": str(price),
                "market_cap": str(market_cap),
                "volume_24h": str(volume),
                "published_at": None,
                "fetched_at": datetime.now().isoformat(),
                "coin_circulating": str(circulating),
                "url": url
            })

    return results

# ===================== BOUCLE DE PARSING =====================

def run_all() -> List[Dict[str, Any]]:
    """Parse all configured URLs and return aggregated items."""
    aggregated: List[Dict[str, Any]] = []

    for url in urls_to_parse:
        domain = url.split("/")[2].replace("www.", "")
        domain_key = ".".join(domain.split(".")[-2:])
        parser_func = SITE_PARSERS.get(domain_key)

        if parser_func:
            print(f"Parsing {url} with {parser_func.__name__}")
            try:
                r = session.get(url)

                if domain_key in ["coinmarketcap.com", "binance.com"]:
                    data = r.json()
                    results = parser_func(url, data)
                else:
                    soup = BeautifulSoup(r.html.html, "lxml")
                    results = parser_func(url, soup)

                print(f"{len(results)} items parsed from {domain_key}")
                print(results)
                aggregated.extend(results)
            except Exception as e:
                print(f"Erreur lors du parsing de {url}: {e}")
        else:
            print(f"Aucun parser trouvé pour {domain_key}")

    return aggregated


if __name__ == "__main__":
    results = run_all()
    print(f"Total items parsed: {len(results)}")
    print(results)
