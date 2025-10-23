from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, validator


class ArticleModel(BaseModel):
    """Normalized article item for NDJSON output and deduplication.

    Fields:
    - id: Stable SHA1 of url + title (lowercased, stripped)
    - title: Article title
    - url: Canonical article URL
    - source: Provider identifier (e.g., "coindesk", "cointelegraph")
    - published_at: Datetime the article was published (UTC)
    - fetched_at: Datetime the article was fetched (UTC)
    """

    id: str
    title: str
    url: HttpUrl
    source: str
    published_at: datetime
    fetched_at: datetime
    content: Optional[str] = None
    is_fallback: bool = False

    @staticmethod
    def generate_id(url: str, title: str) -> str:
        normalized = (url or "").strip().lower() + "|" + (title or "").strip().lower()
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    @validator("title")
    def _title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v.strip()

    @validator("source")
    def _source_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source must be a non-empty string")
        return v.strip().lower()

    @validator("content")
    def _content_strip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        s = v.strip()
        return s if s else None

    @validator("published_at", "fetched_at", pre=True)
    def _coerce_datetime(cls, v: Optional[datetime]):
        if isinstance(v, datetime):
            return v
        # Accept ISO strings
        if isinstance(v, str):
            try:
                # Avoid extra deps; rely on fromisoformat if possible
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                raise ValueError(f"invalid datetime: {v}")
        raise ValueError("datetime required")

    @validator("id", pre=True, always=True)
    def _ensure_id(cls, v: Optional[str], values):
        if v:
            return v
        url = values.get("url")
        title = values.get("title")
        if url is None or title is None:
            raise ValueError("cannot compute id without url and title")
        return ArticleModel.generate_id(str(url), str(title))


