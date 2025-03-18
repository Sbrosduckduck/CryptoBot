import requests
import logging
from typing import Dict, List, Any, Optional

from config import CRYPTO_API_URL, CRYPTO_API_KEY, SUPPORTED_CRYPTOS

def get_crypto_price(crypto_id: str) -> Optional[float]:
    """Get current price of a cryptocurrency in USD."""
    try:
        url = f"{CRYPTO_API_URL}/simple/price"
        params = {
            "ids": crypto_id,
            "vs_currencies": "usd"
        }
        
        # Add API key if provided
        if CRYPTO_API_KEY:
            params["x_cg_pro_api_key"] = CRYPTO_API_KEY
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if crypto_id in data and "usd" in data[crypto_id]:
            return data[crypto_id]["usd"]
        
        logging.warning(f"No price data for {crypto_id}")
        return None
    except Exception as e:
        logging.error(f"Error getting crypto price: {e}")
        return None

def get_multiple_crypto_prices() -> Dict[str, float]:
    """Get current prices for all supported cryptocurrencies."""
    try:
        url = f"{CRYPTO_API_URL}/simple/price"
        params = {
            "ids": ",".join(SUPPORTED_CRYPTOS.keys()),
            "vs_currencies": "usd"
        }
        
        # Add API key if provided
        if CRYPTO_API_KEY:
            params["x_cg_pro_api_key"] = CRYPTO_API_KEY
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract prices for each crypto
        prices = {}
        for crypto_id in SUPPORTED_CRYPTOS.keys():
            if crypto_id in data and "usd" in data[crypto_id]:
                prices[crypto_id] = data[crypto_id]["usd"]
            else:
                prices[crypto_id] = 0.0
                
        return prices
    except Exception as e:
        logging.error(f"Error getting multiple crypto prices: {e}")
        return {crypto_id: 0.0 for crypto_id in SUPPORTED_CRYPTOS.keys()}

def get_crypto_info(crypto_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a cryptocurrency."""
    try:
        url = f"{CRYPTO_API_URL}/coins/{crypto_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        }
        
        # Add API key if provided
        if CRYPTO_API_KEY:
            params["x_cg_pro_api_key"] = CRYPTO_API_KEY
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant information
        info = {
            "id": data.get("id", ""),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name", ""),
            "market_cap_rank": data.get("market_cap_rank", 0),
            "current_price": data.get("market_data", {}).get("current_price", {}).get("usd", 0),
            "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd", 0),
            "total_volume": data.get("market_data", {}).get("total_volume", {}).get("usd", 0),
            "price_change_24h": data.get("market_data", {}).get("price_change_24h", 0),
            "price_change_percentage_24h": data.get("market_data", {}).get("price_change_percentage_24h", 0),
            "description": data.get("description", {}).get("en", "No description available.")
        }
        
        return info
    except Exception as e:
        logging.error(f"Error getting crypto info: {e}")
        return None

def get_trending_cryptos() -> List[Dict[str, Any]]:
    """Get trending cryptocurrencies."""
    try:
        url = f"{CRYPTO_API_URL}/search/trending"
        
        params = {}
        # Add API key if provided
        if CRYPTO_API_KEY:
            params["x_cg_pro_api_key"] = CRYPTO_API_KEY
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        trending = []
        if "coins" in data:
            for item in data["coins"]:
                coin = item.get("item", {})
                trending.append({
                    "id": coin.get("id", ""),
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", "").upper(),
                    "market_cap_rank": coin.get("market_cap_rank", 0)
                })
                
        return trending
    except Exception as e:
        logging.error(f"Error getting trending cryptos: {e}")
        return []

def get_market_data() -> List[Dict[str, Any]]:
    """Get market data for supported cryptocurrencies."""
    try:
        url = f"{CRYPTO_API_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ",".join(SUPPORTED_CRYPTOS.keys()),
            "order": "market_cap_desc",
            "per_page": 25,
            "page": 1,
            "sparkline": "false"
        }
        
        # Add API key if provided
        if CRYPTO_API_KEY:
            params["x_cg_pro_api_key"] = CRYPTO_API_KEY
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant information
        market_data = []
        for coin in data:
            market_data.append({
                "id": coin.get("id", ""),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "image": coin.get("image", ""),
                "current_price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0),
                "market_cap_rank": coin.get("market_cap_rank", 0),
                "total_volume": coin.get("total_volume", 0),
                "price_change_24h": coin.get("price_change_24h", 0),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h", 0),
                "circulating_supply": coin.get("circulating_supply", 0),
                "total_supply": coin.get("total_supply", 0),
                "max_supply": coin.get("max_supply", 0),
                "last_updated": coin.get("last_updated", "")
            })
                
        return market_data
    except Exception as e:
        logging.error(f"Error getting market data: {e}")
        return []
