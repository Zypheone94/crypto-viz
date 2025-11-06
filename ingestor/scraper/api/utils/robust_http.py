import os
import time
import logging
import requests

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 10))
HTTP_MAX_BACKOFF = int(os.getenv("HTTP_MAX_BACKOFF", 300))
HTTP_RETRY_BASE = int(os.getenv("HTTP_RETRY_BASE", 5))

RETRY_STATUS = {429} | set(range(500, 600))

def robust_request(method, url, **kwargs):
    backoff = HTTP_RETRY_BASE
    while True:
        try:
            resp = requests.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)
            if resp.status_code in RETRY_STATUS:
                logging.warning(f"HTTP {resp.status_code} on {url}, retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 3, HTTP_MAX_BACKOFF)
                continue
            # Succès
            if backoff != HTTP_RETRY_BASE:
                logging.info(f"Recovered: {url}")
            return resp
        except (requests.Timeout, requests.ConnectionError) as e:
            logging.warning(f"Network error on {url}: {e}, retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 3, HTTP_MAX_BACKOFF)
        except Exception as e:
            logging.error(f"Fatal error on {url}: {e}")
            raise
    # Remise à zéro du backoff si succès (déjà géré par le return)
