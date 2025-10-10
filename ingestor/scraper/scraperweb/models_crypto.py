from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, validator, Field


class CryptoPriceModel(BaseModel):
    """Model for cryptocurrency price data.
    
    Fields:
    - id: Unique identifier in format: source_coinid_timestamp
    - source: Data source (e.g., "coingecko")
    - type: Data type (e.g., "crypto_price")
    - name: Cryptocurrency name
    - symbol: Cryptocurrency symbol (uppercase)
    - current_price: Current price in USD
    - market_cap: Market capitalization in USD
    - market_cap_rank: Market cap rank
    - total_volume: 24h trading volume in USD
    - price_change_24h: Absolute price change in 24h
    - price_change_percentage_24h: Percentage price change in 24h
    - high_24h: 24h high
    - low_24h: 24h low
    - circulating_supply: Circulating supply
    - total_supply: Total supply
    - max_supply: Maximum supply (if applicable)
    - fetched_at: Datetime when data was fetched (UTC)
    - published_at: Datetime when data was published (UTC)
    """

    id: str
    source: str
    type: str = "crypto_price"
    name: str
    symbol: str
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_rank: Optional[int] = None
    total_volume: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    fetched_at: datetime
    published_at: datetime
    
    @validator("symbol")
    def _symbol_uppercase(cls, v: str) -> str:
        return v.upper() if v else ""
    
    @validator("source")
    def _source_lowercase(cls, v: str) -> str:
        return v.lower() if v else ""
        
    @validator("published_at", "fetched_at", pre=True)
    def _coerce_datetime(cls, v: Optional[datetime]):
        if isinstance(v, datetime):
            return v
        # Accept ISO strings
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                raise ValueError(f"invalid datetime: {v}")
        raise ValueError("datetime required")

class ChatGPTPrompt(BaseModel):
    """Model for generating prompts for ChatGPT financial analysis.
    
    Fields:
    - prompt_id: Unique identifier for the prompt
    - timestamp: When the prompt was generated
    - top_coins: List of top cryptocurrencies with their data
    - prompt_text: Generated prompt for ChatGPT
    """
    
    prompt_id: str = Field(..., description="Unique ID for the prompt")
    timestamp: datetime = Field(default_factory=lambda: datetime.now().isoformat())
    top_coins: List[Dict[str, Any]] = Field(..., description="List of top cryptocurrency data")
    prompt_text: str = Field(..., description="Generated prompt for ChatGPT")