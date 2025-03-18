
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from database import get_db

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_pending_transactions():
    """Проверяет наличие и статус активных заявок в базе данных"""
    logger.info("Проверяем активные заявки...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Проверяем структуру таблицы transactions
            cursor.execute("PRAGMA table_info(transactions)")
            columns = cursor.fetchall()
            logger.info(f"Структура таблицы transactions: {[col[1] for col in columns]}")
            
            # Проверяем индексы на таблице
            cursor.execute("PRAGMA index_list('transactions')")
            indexes = cursor.fetchall()
            logger.info(f"Индексы таблицы transactions: {indexes}")
            
            # Считаем общее количество транзакций
            cursor.execute("SELECT COUNT(*) FROM transactions")
            total_transactions = cursor.fetchone()[0]
            logger.info(f"Всего транзакций в базе: {total_transactions}")
            
            # Получаем все транзакции со статусом 'pending'
            cursor.execute('''
                SELECT t.*, u.first_name, u.last_name, u.email
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.status = ?
            ''', ('pending',))
            
            pending_transactions = cursor.fetchall()
            logger.info(f"Найдено {len(pending_transactions)} активных заявок со статусом 'pending'")
            
            # Выводим детали каждой активной заявки
            for tx in pending_transactions:
                logger.info(f"Заявка ID: {tx['id']}, Уникальный ID: {tx['unique_id']}, "
                          f"Тип: {tx['type']}, Сумма: {tx['amount']}, "
                          f"Пользователь: {tx['first_name']} {tx['last_name']}")
            
            # Проверяем заявки без unique_id
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE unique_id IS NULL")
            null_unique_ids = cursor.fetchone()[0]
            logger.info(f"Транзакций без unique_id: {null_unique_ids}")
            
            if null_unique_ids > 0:
                cursor.execute("SELECT id, type, amount, status FROM transactions WHERE unique_id IS NULL")
                tx_without_ids = cursor.fetchall()
                logger.info(f"Заявки без unique_id: {[dict(tx) for tx in tx_without_ids]}")
            
            return {
                "total_transactions": total_transactions,
                "pending_transactions": len(pending_transactions),
                "transactions_without_unique_id": null_unique_ids,
                "pending_details": [dict(tx) for tx in pending_transactions]
            }
            
    except Exception as e:
        logger.error(f"Ошибка при проверке заявок: {e}")
        logger.exception("Полные детали ошибки:")
        return {"error": str(e)}

def test_unique_id_generation():
    """Тестирует генерацию уникальных ID"""
    from database import generate_unique_id
    
    logger.info("Тестируем генерацию уникальных ID...")
    
    try:
        # Генерируем несколько ID для проверки
        ids = [generate_unique_id() for _ in range(5)]
        logger.info(f"Сгенерированные ID: {ids}")
        
        # Проверяем уникальность
        unique_ids = set(ids)
        logger.info(f"Уникальных ID: {len(unique_ids)} из {len(ids)}")
        
        # Проверяем длину (для отображения последних 6 цифр)
        logger.info(f"Длина ID: {len(str(ids[0]))}")
        logger.info(f"Последние 6 цифр: {str(ids[0])[-6:]}")
        
        return {
            "generated_ids": ids,
            "unique_count": len(unique_ids),
            "id_length": len(str(ids[0])),
            "last_6_digits": [str(id)[-6:] for id in ids]
        }
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании генерации ID: {e}")
        logger.exception("Полные детали ошибки:")
        return {"error": str(e)}

if __name__ == "__main__":
    print("=== Проверка активных заявок ===")
    transactions_info = check_pending_transactions()
    print(f"Всего транзакций: {transactions_info['total_transactions']}")
    print(f"Активных заявок: {transactions_info['pending_transactions']}")
    print(f"Транзакций без unique_id: {transactions_info['transactions_without_unique_id']}")
    
    print("\n=== Тест генерации уникальных ID ===")
    unique_id_info = test_unique_id_generation()
    print(f"Сгенерированные ID: {unique_id_info['generated_ids']}")
    print(f"Уникальность: {unique_id_info['unique_count']} из {len(unique_id_info['generated_ids'])}")
    print(f"Длина ID: {unique_id_info['id_length']}")
    print(f"Последние 6 цифр: {unique_id_info['last_6_digits']}")
