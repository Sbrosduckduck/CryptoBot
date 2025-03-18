import sqlite3
from config import DATABASE_NAME
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_cryptocurrencies():
    """Проверяет наличие и состояние криптовалют в базе данных"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM cryptocurrencies')
        cryptos = cursor.fetchall()

        print("\nCryptocurrencies in database:")
        print("-" * 50)
        if cryptos:
            for crypto in cryptos:
                print(f"Name: {crypto['name']}")
                print(f"Symbol: {crypto['symbol']}")
                print(f"Rate: {crypto['rate']}")
                print(f"Total Supply: {crypto['total_supply']}")
                print(f"Available Supply: {crypto['available_supply']}")
                print("-" * 50)
            return len(cryptos)
        else:
            print("No cryptocurrencies found in database")
            return 0

    except Exception as e:
        logger.error(f"Error checking database: {e}")
        return 0
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Database connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

if __name__ == "__main__":
    count = check_cryptocurrencies()
    print(f"\nTotal cryptocurrencies found: {count}")