import sqlite3
from contextlib import contextmanager
from typing import List, Tuple, Dict, Optional
import datetime
import logging
from config import DATABASE_NAME

# Assuming a basic logger setup.  This should be improved in a production environment.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # Таблица пользователей остается без изменений

        # Таблица для истории цен криптовалют
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crypto_id INTEGER,
            rate REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crypto_id) REFERENCES cryptocurrencies (id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            middle_name TEXT,
            birth_date TEXT,
            email TEXT,
            phone TEXT,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Обновленная таблица криптовалют
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cryptocurrencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            symbol TEXT UNIQUE,
            rate REAL,
            total_supply REAL,
            available_supply REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица портфелей пользователей остается без изменений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            user_id INTEGER,
            crypto_id INTEGER,
            amount REAL,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (crypto_id) REFERENCES cryptocurrencies (id)
        )
        ''')

        # Таблица транзакций остается без изменений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            status TEXT,
            unique_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        conn.commit()

def add_user(user_data: Dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (user_id, first_name, last_name, middle_name, birth_date, email, phone)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data['user_id'],
            user_data['first_name'],
            user_data['last_name'],
            user_data['middle_name'],
            user_data['birth_date'],
            user_data['email'],
            user_data['phone']
        ))
        conn.commit()

def get_user(user_id: int) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

def generate_unique_id():
    """Generates a unique transaction ID"""
    import time
    import random
    timestamp = int(time.time() * 1000)
    random_num = random.randint(100, 999)
    return f"{timestamp}{random_num}"

def add_transaction(user_id: int, type_: str, amount: float, status: str = 'pending'):
    with get_db() as conn:
        cursor = conn.cursor()
        unique_id = generate_unique_id()
        cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, status, unique_id)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, type_, amount, status, unique_id))
        conn.commit()
        return cursor.lastrowid

def validate_crypto_symbol(symbol: str) -> bool:
    """Проверяет формат символа криптовалюты (3 заглавные + 1 строчная)"""
    if len(symbol) != 4:
        return False
    return symbol[:3].isupper() and symbol[3].islower()

def add_crypto(name: str, symbol: str, rate: float, total_supply: float):
    if not validate_crypto_symbol(symbol):
        raise ValueError("Символ должен состоять из 3 заглавных и 1 строчной буквы (например: BTCd)")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO cryptocurrencies (name, symbol, rate, total_supply, available_supply)
        VALUES (?, ?, ?, ?, ?)
        ''', (name, symbol, rate, total_supply, total_supply))
        conn.commit()

def update_crypto(crypto_id: int, rate: Optional[float] = None, total_supply: Optional[float] = None, available_supply: Optional[float] = None):
    """
    Обновляет параметры криптовалюты
    :param crypto_id: ID криптовалюты
    :param rate: Новый курс в рублях
    :param total_supply: Новое общее количество монет
    :param available_supply: Новое доступное количество монет
    """
    updates = []
    values = []

    if rate is not None:
        updates.append("rate = ?")
        values.append(rate)
    if total_supply is not None:
        updates.append("total_supply = ?")
        values.append(total_supply)
        if available_supply is None:  # Если available_supply не указан, устанавливаем = total_supply
            updates.append("available_supply = ?")
            values.append(total_supply)
    if available_supply is not None:
        updates.append("available_supply = ?")
        values.append(available_supply)

    if not updates:
        return

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(crypto_id)  # Для WHERE id = ?

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
        UPDATE cryptocurrencies 
        SET {', '.join(updates)}
        WHERE id = ?
        ''', values)
        conn.commit()

def buy_crypto(user_id: int, crypto_id: int, amount: float) -> bool:
    """
    Покупка криптовалюты пользователем
    :param user_id: ID пользователя
    :param crypto_id: ID криптовалюты
    :param amount: Количество криптовалюты для покупки
    :return: True если покупка успешна, False в противном случае
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Начинаем транзакцию
        conn.execute("BEGIN TRANSACTION")

        try:
            # Получаем данные криптовалюты
            cursor.execute("SELECT * FROM cryptocurrencies WHERE id = ?", (crypto_id,))
            crypto = cursor.fetchone()
            if not crypto:
                conn.rollback()
                return False

            # Проверяем, есть ли достаточное количество криптовалюты
            if crypto['available_supply'] < amount:
                conn.rollback()
                return False

            # Вычисляем стоимость покупки
            cost = crypto['rate'] * amount

            # Получаем данные пользователя
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                conn.rollback()
                return False

            # Проверяем, достаточно ли у пользователя средств
            if user['balance'] < cost:
                conn.rollback()
                return False

            # Уменьшаем баланс пользователя
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (cost, user_id)
            )

            # Уменьшаем доступное количество криптовалюты
            cursor.execute(
                "UPDATE cryptocurrencies SET available_supply = available_supply - ? WHERE id = ?",
                (amount, crypto_id)
            )

            # Проверяем, есть ли у пользователя уже эта криптовалюта
            cursor.execute(
                "SELECT * FROM portfolios WHERE user_id = ? AND crypto_id = ?",
                (user_id, crypto_id)
            )
            portfolio_entry = cursor.fetchone()

            if portfolio_entry:
                # Обновляем существующую запись
                cursor.execute(
                    "UPDATE portfolios SET amount = amount + ? WHERE user_id = ? AND crypto_id = ?",
                    (amount, user_id, crypto_id)
                )
            else:
                # Создаем новую запись
                cursor.execute(
                    "INSERT INTO portfolios (user_id, crypto_id, amount) VALUES (?, ?, ?)",
                    (user_id, crypto_id, amount)
                )

            # Фиксируем изменения
            conn.commit()
            return True

        except Exception as e:
            # В случае ошибки отменяем все изменения
            conn.rollback()
            logging.error(f"Error in buy_crypto: {e}")
            return False

def sell_crypto(user_id: int, crypto_id: int, amount: float) -> bool:
    """
    Продажа криптовалюты пользователем обратно системе
    :param user_id: ID пользователя
    :param crypto_id: ID криптовалюты
    :param amount: Количество криптовалюты для продажи
    :return: True если продажа успешна, False в противном случае
    """
    logger.info(f"Attempting to sell crypto: user_id={user_id}, crypto_id={crypto_id}, amount={amount}")

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Начинаем транзакцию
            conn.execute("BEGIN TRANSACTION")

            # Получаем данные криптовалюты
            cursor.execute("SELECT * FROM cryptocurrencies WHERE id = ?", (crypto_id,))
            crypto = cursor.fetchone()
            if not crypto:
                logger.error(f"Cryptocurrency {crypto_id} not found")
                conn.rollback()
                return False

            # Получаем текущий портфель пользователя
            cursor.execute(
                "SELECT amount FROM portfolios WHERE user_id = ? AND crypto_id = ?",
                (user_id, crypto_id)
            )
            portfolio = cursor.fetchone()

            if not portfolio:
                logger.error(f"No portfolio entry found for user {user_id} and crypto {crypto_id}")
                conn.rollback()
                return False

            current_amount = portfolio['amount']
            if current_amount < amount:
                logger.error(f"Insufficient crypto amount: has {current_amount}, trying to sell {amount}")
                conn.rollback()
                return False

            # Вычисляем стоимость продажи
            sale_value = crypto['rate'] * amount

            # Обновляем баланс пользователя
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (sale_value, user_id)
            )

            # Обновляем количество криптовалюты в портфеле
            new_amount = current_amount - amount
            if new_amount > 0:
                cursor.execute(
                    "UPDATE portfolios SET amount = ? WHERE user_id = ? AND crypto_id = ?",
                    (new_amount, user_id, crypto_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM portfolios WHERE user_id = ? AND crypto_id = ?",
                    (user_id, crypto_id)
                )

            # Обновляем доступное предложение криптовалюты
            cursor.execute(
                "UPDATE cryptocurrencies SET available_supply = available_supply + ? WHERE id = ?",
                (amount, crypto_id)
            )

            # Создаем запись о транзакции
            cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, status) VALUES (?, ?, ?, ?)",
                (user_id, 'sell_crypto', sale_value, 'completed')
            )

            # Фиксируем изменения
            conn.commit()
            logger.info(f"Successfully sold {amount} of crypto {crypto_id} for user {user_id}")
            return True

        except Exception as e:
            # В случае ошибки отменяем все изменения
            conn.rollback()
            logger.error(f"Error in sell_crypto: {e}")
            logger.exception("Full error details:")
            return False

def get_all_cryptos(include_private: bool = False) -> List[Dict]:
    """
    Получает список всех криптовалют
    :param include_private: если True, включает приватные данные (total_supply)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if include_private:
                cursor.execute('SELECT * FROM cryptocurrencies')
            else:
                cursor.execute('''
                SELECT id, name, symbol, rate, available_supply, 
                       created_at, updated_at 
                FROM cryptocurrencies
                ''')
            cryptos = cursor.fetchall()
            if cryptos:
                logger.info(f"get_all_cryptos: получено {len(cryptos)} криптовалют")
                for crypto in cryptos:
                    logger.info(f"Криптовалюта: id={crypto['id']}, name={crypto['name']}, symbol={crypto['symbol']}, rate={crypto['rate']}")
                return [dict(row) for row in cryptos]
            else:
                logger.info("get_all_cryptos: криптовалюты не найдены")
                return []
    except Exception as e:
        logger.error(f"Ошибка в get_all_cryptos: {e}")
        return []

def get_crypto_by_id(crypto_id: int, include_private: bool = False) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        if include_private:
            cursor.execute('SELECT * FROM cryptocurrencies WHERE id = ?', (crypto_id,))
        else:
            cursor.execute("""
            SELECT id, name, symbol, rate, available_supply 
            FROM cryptocurrencies 
            WHERE id = ?
            """, (crypto_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

def add_price_history(crypto_id: int, rate: float):
    """
    Добавляет запись об изменении цены криптовалюты
    :param crypto_id: ID криптовалюты
    :param rate: Текущий курс
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO crypto_price_history (crypto_id, rate)
            VALUES (?, ?)
            ''', (crypto_id, rate))
            conn.commit()
    except Exception as e:
        logger.error(f"Error adding price history: {e}")

def get_price_history(crypto_id: int, days: int = 30) -> List[Dict]:
    """
    Получает историю цен криптовалюты за указанный период
    :param crypto_id: ID криптовалюты
    :param days: Количество дней для получения истории
    :return: Список записей с ценами и датами
    """
    try:
        logger.info(f"Fetching price history for crypto_id={crypto_id}, days={days}")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT rate, timestamp
            FROM crypto_price_history
            WHERE crypto_id = ? AND timestamp >= datetime('now', ?) 
            ORDER BY timestamp
            ''', (crypto_id, f'-{days} days'))

            history = cursor.fetchall()
            if history:
                logger.info(f"Found {len(history)} price records")
                logger.debug(f"First record: {history[0]}")
                logger.debug(f"Last record: {history[-1]}")
            else:
                logger.warning(f"No price history found for crypto_id={crypto_id}")
            return [dict(row) for row in history] if history else []
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        logger.exception("Full error details:")
        return []

def update_crypto_with_history(crypto_id: int, rate: float, total_supply: Optional[float] = None, available_supply: Optional[float] = None):
    """
    Обновляет параметры криптовалюты и добавляет запись в историю цен
    :param crypto_id: ID криптовалюты
    :param rate: Новый курс в рублях
    :param total_supply: Новое общее количество монет
    :param available_supply: Новое доступное количество монет
    """
    # Обновляем данные криптовалюты
    update_crypto(crypto_id, rate, total_supply, available_supply)

    # Добавляем запись в историю цен
    add_price_history(crypto_id, rate)

def get_pending_transactions():
    """
    Получает список всех транзакций со статусом 'pending' с информацией о пользователях
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, u.first_name, u.last_name, u.email
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.status = ?
                ORDER BY t.created_at DESC
            ''', ('pending',))
            transactions = cursor.fetchall()
            logger.debug(f"Retrieved {len(transactions) if transactions else 0} pending transactions")
            return [dict(tx) for tx in transactions] if transactions else []
    except Exception as e:
        logger.error(f"Error getting pending transactions: {e}")
        logger.exception("Full error details:")
        return []

def update_transaction_status(tx_id: int, new_status: str) -> bool:
    """
    Обновляет статус транзакции
    :param tx_id: ID транзакции
    :param new_status: Новый статус ('completed' или 'rejected')
    :return: True если обновление успешно, False в противном случае
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE transactions SET status = ? WHERE id = ? AND status = ?",
                (new_status, tx_id, 'pending')
            )
            conn.commit()
            affected = cursor.rowcount
            logger.debug(f"Updated transaction {tx_id} to status {new_status}, affected rows: {affected}")
            return affected > 0
    except Exception as e:
        logger.error(f"Error updating transaction status: {e}")
        logger.exception("Full error details:")
        return False

def update_user_balance(user_id: int, new_balance: float) -> bool:
    """
    Обновляет баланс пользователя
    :param user_id: ID пользователя
    :param new_balance: Новый баланс
    :return: True если обновление успешно, False в противном случае
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = ? WHERE user_id = ?",
                (new_balance, user_id)
            )
            conn.commit()
            affected = cursor.rowcount
            logger.debug(f"Updated balance for user {user_id} to {new_balance}, affected rows: {affected}")
            return affected > 0
    except Exception as e:
        logger.error(f"Error updating user balance: {e}")
        logger.exception("Full error details:")
        return False