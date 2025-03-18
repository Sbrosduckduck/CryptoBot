from database import add_crypto, init_db

def add_test_cryptocurrencies():
    # Инициализируем базу данных
    init_db()
    
    # Список тестовых криптовалют
    test_cryptos = [
        ("Bitcoin", "BTCd", 3500000.0, 21000000.0),
        ("Ethereum", "ETHd", 190000.0, 120000000.0),
        ("Dogecoin", "DGEd", 7.5, 132670764264.0)
    ]
    
    # Добавляем каждую криптовалюту
    for name, symbol, rate, supply in test_cryptos:
        try:
            add_crypto(name, symbol, rate, supply)
            print(f"Added {name} ({symbol})")
        except Exception as e:
            print(f"Error adding {name}: {e}")

if __name__ == "__main__":
    add_test_cryptocurrencies()
