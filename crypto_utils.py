import requests
from typing import Dict, Optional
from logger import logger
from config import CRYPTO_API_KEY, CRYPTO_API_URL, SUPPORTED_CRYPTO

class CryptoAPI:
    def __init__(self):
        self.api_key = CRYPTO_API_KEY
        self.base_url = CRYPTO_API_URL

    def get_price(self, crypto: str) -> Optional[float]:
        """Get current price for cryptocurrency"""
        try:
            if crypto not in SUPPORTED_CRYPTO:
                return None
            
            response = requests.get(
                f"{self.base_url}/simple/price",
                params={
                    'ids': SUPPORTED_CRYPTO[crypto].lower(),
                    'vs_currencies': 'usd'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data[SUPPORTED_CRYPTO[crypto].lower()]['usd']
            return None
        except Exception as e:
            logger.error(f"Error fetching crypto price: {e}")
            return None

    def validate_address(self, crypto: str, address: str) -> bool:
        """Validate cryptocurrency address format"""
        # Basic validation patterns - in real implementation should use proper validation libraries
        patterns = {
            'BTC': lambda x: len(x) >= 26 and len(x) <= 35 and (x.startswith('1') or x.startswith('3') or x.startswith('bc1')),
            'ETH': lambda x: len(x) == 42 and x.startswith('0x'),
            'USDT': lambda x: len(x) == 42 and x.startswith('0x'),  # ERC-20 USDT
            'BNB': lambda x: len(x) == 42 and x.startswith('0x')  # BEP-20 BNB
        }
        
        try:
            return patterns.get(crypto, lambda x: False)(address)
        except Exception as e:
            logger.error(f"Error validating address: {e}")
            return False

crypto_api = CryptoAPI()
