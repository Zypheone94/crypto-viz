"""
ChatGPT Prompt Generator for Cryptocurrency Analysis
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
import glob

from models_crypto import ChatGPTPrompt
from logging_json import log_json


def load_crypto_data(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Load the most recent cryptocurrency data from NDJSON files.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        List of cryptocurrency data dictionaries
    """
    # Check both scraper/data and parent data directories
    current_dir = Path(__file__).resolve().parent
    scraper_data_dir = current_dir.parent / "data"
    parent_data_dir = current_dir.parent.parent / "data"
    
    data_files = []
    
    # Look for the most recent price data files in both locations
    for check_dir in [scraper_data_dir, parent_data_dir]:
        raw_data_pattern = check_dir / "raw" / "*" / "*" / "*" / "part-coindesk_price_data-*.ndjson"
        found_files = list(glob.glob(str(raw_data_pattern)))
        data_files.extend(found_files)
    
    if not data_files:
        log_json("warning", "No CoinDesk price data files found", 
               patterns=[str(scraper_data_dir / "raw"), str(parent_data_dir / "raw")])
        return []
    
    # Sort by filename (timestamp) to get most recent
    data_files.sort(reverse=True)
    most_recent_file = data_files[0]
    
    log_json("info", "Loading crypto data for prompt generation", file=most_recent_file)
    
    # Load the crypto data
    crypto_data = []
    try:
        with open(most_recent_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if (item.get('type') == 'crypto_price' and 
                        item.get('source') == 'coindesk_price' and 
                        item.get('current_price') is not None):
                        crypto_data.append(item)
                except json.JSONDecodeError as e:
                    log_json("debug", f"JSON decode error: {str(e)}", line=line[:100])
                    continue
    except Exception as e:
        log_json("error", f"Error loading crypto data: {str(e)}")
        return []
    
    # Sort by market cap if available, otherwise by current price
    def sort_key(item):
        market_cap = item.get('market_cap')
        if market_cap and market_cap > 0:
            return market_cap
        # If no market cap, estimate by price (higher price coins first)
        price = item.get('current_price', 0)
        return price * 1000000  # Give some weight to price
    
    sorted_data = sorted(crypto_data, key=sort_key, reverse=True)
    
    log_json("info", f"Loaded {len(sorted_data)} cryptocurrencies for prompt generation",
             sample_symbols=[item.get('symbol') for item in sorted_data[:3]])
    return sorted_data


def generate_prompt(crypto_data: List[Dict[str, Any]]) -> str:
    """
    Generate a prompt for ChatGPT based on cryptocurrency data.
    
    Args:
        crypto_data: List of cryptocurrency data dictionaries
        
    Returns:
        A prompt for ChatGPT
    """
    if not crypto_data:
        return "No cryptocurrency data available for analysis."
    
    # Get top 10 cryptocurrencies
    top_coins = crypto_data[:10]
    
    # Format the data for the prompt
    coins_text = ""
    for i, coin in enumerate(top_coins, 1):
        price_change = coin.get('price_change_percentage_24h') or 0
        change_arrow = "📈" if price_change >= 0 else "📉"
        
        # Handle null values gracefully
        price = coin.get('current_price') or 0
        market_cap = coin.get('market_cap')
        volume = coin.get('total_volume')
        rank = coin.get('market_cap_rank')
        
        coins_text += f"{i}. {coin.get('name', 'Unknown')} ({coin.get('symbol', 'N/A')})\n"
        coins_text += f"   Price: ${price:,.4f}\n"
        
        if price_change:
            coins_text += f"   24h Change: {change_arrow} {abs(price_change):.2f}%\n"
        else:
            coins_text += "   24h Change: No data\n"
            
        if market_cap and market_cap > 0:
            coins_text += f"   Market Cap: ${market_cap:,.0f}\n"
        else:
            coins_text += "   Market Cap: No data\n"
            
        if rank:
            coins_text += f"   Market Cap Rank: #{rank}\n"
        else:
            coins_text += "   Market Cap Rank: No data\n"
            
        if volume and volume > 0:
            coins_text += f"   24h Volume: ${volume:,.0f}\n"
        else:
            coins_text += "   24h Volume: No data\n"
            
        coins_text += "\n"
    
    # Create timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Count how many have complete data
    complete_data_count = sum(1 for coin in top_coins 
                            if coin.get('market_cap') and coin.get('price_change_percentage_24h'))
    
    # Generate the prompt
    prompt = f"""
As a cryptocurrency financial analyst, provide insights on the current market conditions based on the following CoinDesk price data from {timestamp}:

{coins_text}
📊 Data Completeness: {complete_data_count}/{len(top_coins)} cryptocurrencies have complete market data.

Based on this CoinDesk price data, please provide:

1. **Market Overview**: Current state of the cryptocurrency market
2. **Price Analysis**: Notable price levels and movements for major cryptocurrencies
3. **Market Trends**: Patterns visible in the available price data
4. **Technical Outlook**: Short-term analysis for Bitcoin, Ethereum, and other major coins
5. **Risk Assessment**: Current market risk factors and considerations
6. **Data Insights**: What the available/missing data tells us about market transparency

Please structure your analysis in a clear, professional format suitable for crypto investors and traders.

Note: Some market cap and volume data may be incomplete due to CoinDesk data limitations.
"""
    return prompt.strip()


def save_prompt(prompt_text: str, top_coins: List[Dict[str, Any]], output_dir: Path) -> None:
    """
    Save the generated prompt to a file.
    
    Args:
        prompt_text: The generated prompt text
        top_coins: List of top cryptocurrency data
        output_dir: Directory to save the prompt
    """
    # Create a unique ID based on timestamp
    timestamp = datetime.now(timezone.utc)
    prompt_id = f"crypto_analysis_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    
    # Create the prompt object with proper timestamp formatting
    prompt = ChatGPTPrompt(
        prompt_id=prompt_id,
        timestamp=timestamp.isoformat(),
        top_coins=top_coins[:10],  # Include only top 10
        prompt_text=prompt_text
    )
    
    # Ensure prompts directory exists
    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as NDJSON format
    output_file = prompts_dir / f"{prompt_id}.ndjson"
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert the prompt to dict and handle datetime serialization
        prompt_dict = prompt.model_dump()
        json.dump(prompt_dict, f, ensure_ascii=False, default=str, separators=(',', ':'))
        f.write('\n')
    
    log_json("info", "ChatGPT prompt saved as NDJSON", ndjson_file=str(output_file))
    
    # Save as TXT for easy copy/paste
    txt_output_file = prompts_dir / f"{prompt_id}.txt"
    with open(txt_output_file, 'w', encoding='utf-8') as f:
        f.write(prompt_text)
    
    log_json("info", "ChatGPT prompt saved as text", txt_file=str(txt_output_file))


def generate_chatgpt_prompt() -> None:
    """
    Generate a ChatGPT prompt and save it to a file.
    This function runs on a schedule.
    """
    try:
        log_json("info", "Generating ChatGPT prompt for cryptocurrency analysis")
        
        # Get data path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent.parent / "data"
        
        # Load crypto data
        crypto_data = load_crypto_data(data_dir)
        
        if not crypto_data:
            log_json("warning", "No cryptocurrency data available for prompt generation")
            return
            
        log_json("info", f"Generating prompt with data for {len(crypto_data)} cryptocurrencies")
        
        # Generate prompt
        prompt_text = generate_prompt(crypto_data)
        
        # Save prompt
        save_prompt(prompt_text, crypto_data[:10], data_dir)
        
        log_json("info", "ChatGPT prompt generation completed successfully")
    
    except Exception as e:
        log_json("error", f"Error generating ChatGPT prompt: {str(e)}")