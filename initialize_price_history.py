
import logging
from database import get_db, get_all_cryptos, add_price_history
import time

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_price_history():
    """
    Инициализирует историю цен для существующих криптовалют
    """
    try:
        # Получаем все существующие криптовалюты
        cryptos = get_all_cryptos(include_private=True)
        
        if not cryptos:
            logger.info("Криптовалюты не найдены")
            return
            
        logger.info(f"Найдено {len(cryptos)} криптовалют для инициализации")
        
        # Генерируем тестовые данные для истории цен (за 30 дней)
        for crypto in cryptos:
            crypto_id = crypto['id']
            current_rate = crypto['rate']
            
            # Проверяем, есть ли уже записи
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM crypto_price_history WHERE crypto_id = ?", 
                    (crypto_id,)
                )
                result = cursor.fetchone()
                
                if result and result['count'] > 0:
                    logger.info(f"Для криптовалюты {crypto['symbol']} уже есть {result['count']} записей истории цен")
                    continue
                    
            logger.info(f"Инициализация истории цен для {crypto['name']} ({crypto['symbol']})")
            
            # Добавляем текущую цену
            add_price_history(crypto_id, current_rate)
            
            # Задержка для предотвращения конфликтов с timestamp
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации истории цен: {e}")

if __name__ == "__main__":
    logger.info("Начало инициализации истории цен")
    init_price_history()
    logger.info("Инициализация истории цен завершена")
