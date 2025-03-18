#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from database import get_db, generate_unique_id

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_existing_transactions():
    """Обновляет существующие транзакции, добавляя им уникальные ID"""
    logger.info("Начинаем обновление транзакций...")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Проверяем транзакции без unique_id
            cursor.execute("SELECT id FROM transactions WHERE unique_id IS NULL")
            transactions = cursor.fetchall()

            logger.info(f"Найдено {len(transactions)} транзакций без unique_id")

            # Обновляем каждую транзакцию
            updated_count = 0
            for tx in transactions:
                try:
                    unique_id = generate_unique_id()
                    cursor.execute(
                        "UPDATE transactions SET unique_id = ? WHERE id = ?",
                        (unique_id, tx[0]) # Corrected index access here
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Ошибка при обновлении транзакции {tx[0]}: {e}")

            conn.commit()
            logger.info(f"Обновлено {updated_count} транзакций")
            return updated_count

    except Exception as e:
        logger.error(f"Ошибка при обновлении транзакций: {e}")
        return 0

if __name__ == "__main__":
    count = update_existing_transactions()
    print(f"Обновлено {count} транзакций")