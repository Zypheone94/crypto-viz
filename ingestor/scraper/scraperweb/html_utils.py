"""HTML utilities for the scraper."""
import re
from html import unescape


def strip_html_tags(html_content):
    """Strip HTML tags from content, preserving text."""
    if not html_content:
        return ""
    
    text = unescape(html_content)
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*>', r' \1 ', text)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()