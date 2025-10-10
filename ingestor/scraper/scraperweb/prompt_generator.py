"""
ChatGPT Prompt Generator for Cryptocurrency Analysis
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import threading
from typing import List, Dict, Any

from .models_crypto import ChatGPTPrompt

# Import shutdown_event from main
from . import main
shutdown_event = main.shutdown_event


def load_crypto_data(data_path: Path) -> List[Dict[str, Any]]:
    """
    Load the most recent cryptocurrency data from NDJSON file.
    
    Args:
        data_path: Path to the data directory
        
    Returns:
        List of cryptocurrency data dictionaries
    """
    ndjson_path = data_path / "articles.ndjson"
    if not ndjson_path.exists():
        print(f"No data file found at {ndjson_path}")
        return []
    
    # Load the latest crypto price data
    crypto_prices = []
    try:
        with open(ndjson_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    if item.get('type') == 'crypto_price' and item.get('source') == 'coingecko':
                        crypto_prices.append(item)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error loading crypto data: {e}")
        return []
    
    # Group by symbol and keep most recent for each
    crypto_by_symbol = {}
    for item in crypto_prices:
        symbol = item.get('symbol')
        if not symbol:
            continue
            
        if symbol not in crypto_by_symbol or \
           item.get('fetched_at', '') > crypto_by_symbol[symbol].get('fetched_at', ''):
            crypto_by_symbol[symbol] = item
    
    # Sort by market cap rank
    sorted_crypto = sorted(
        crypto_by_symbol.values(), 
        key=lambda x: x.get('market_cap_rank', float('inf'))
    )
    
    return sorted_crypto


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
        price_change = coin.get('price_change_percentage_24h', 0)
        change_arrow = "↑" if price_change >= 0 else "↓"
        
        coins_text += f"{i}. {coin.get('name')} ({coin.get('symbol')})\n"
        coins_text += f"   Price: ${coin.get('current_price', 0):,.2f}\n"
        coins_text += f"   24h Change: {change_arrow} {abs(price_change):.2f}%\n"
        coins_text += f"   Market Cap: ${coin.get('market_cap', 0):,.0f}\n"
        coins_text += f"   Market Cap Rank: #{coin.get('market_cap_rank', 'N/A')}\n"
        coins_text += f"   24h Volume: ${coin.get('total_volume', 0):,.0f}\n\n"
    
    # Create timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Generate the prompt
    prompt = f"""
As a cryptocurrency financial analyst, provide insights on the current market conditions based on the following data from {timestamp}:

{coins_text}
Based on this data, please provide:

1. A brief overview of the current crypto market conditions
2. Notable price movements and their potential reasons
3. Key market trends and patterns
4. Short-term outlook (24-48 hours) for the top 3 cryptocurrencies
5. Potential impacts of recent news events on these prices
6. Technical analysis highlights for Bitcoin and Ethereum
7. Risk assessment for the current market

Please structure your analysis in a clear, professional format suitable for investors.
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
    
    # Create the prompt object
    prompt = ChatGPTPrompt(
        prompt_id=prompt_id,
        timestamp=timestamp.isoformat(),
        top_coins=top_coins[:10],  # Include only top 10
        prompt_text=prompt_text
    )
    
    # Ensure prompts directory exists
    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    output_file = prompts_dir / f"{prompt_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(prompt.dict(), f, indent=2, ensure_ascii=False)
    
    print(f"Saved ChatGPT prompt to {output_file}")
    
    # Save as TXT for easy copy/paste
    txt_output_file = prompts_dir / f"{prompt_id}.txt"
    with open(txt_output_file, 'w', encoding='utf-8') as f:
        f.write(prompt_text)
    
    print(f"Saved plain text prompt to {txt_output_file}")


def generate_chatgpt_prompt() -> None:
    """
    Generate a ChatGPT prompt and save it to a file.
    This function runs on a schedule.
    """
    try:
        print("Generating ChatGPT prompt for cryptocurrency analysis...")
        
        # Get data path from environment
        data_path = Path(os.getenv("DATA_PATH", "./data"))
        data_path.mkdir(parents=True, exist_ok=True)
        
        # Load crypto data
        crypto_data = load_crypto_data(data_path)
        
        if not crypto_data:
            print("No cryptocurrency data available. Make sure the CoinGecko crawler has run.")
            return
            
        print(f"Loaded data for {len(crypto_data)} cryptocurrencies")
        
        # Generate prompt
        prompt_text = generate_prompt(crypto_data)
        
        # Save prompt
        save_prompt(prompt_text, crypto_data[:10], data_path)
        
        # Schedule next run (every 6 hours by default)
        if not shutdown_event.is_set():  # Import this from the main module
            interval = int(os.getenv("PROMPT_GEN_INTERVAL", "21600"))  # 6 hours
            print(f"Scheduling next prompt generation in {interval} seconds...")
            threading.Timer(interval, generate_chatgpt_prompt).start()
    
    except Exception as e:
        print(f"Error generating ChatGPT prompt: {e}")