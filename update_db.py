
import sqlite3
from config import DATABASE_NAME

def update_transactions_table():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        
        # Add unique_id column if it doesn't exist
        cursor.execute("""
        ALTER TABLE transactions ADD COLUMN unique_id TEXT;
        """)
        
        conn.commit()

if __name__ == "__main__":
    update_transactions_table()

def update_database_schema():
    print("Начинаю обновление схемы базы данных...")
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Проверяем, существуют ли нужные столбцы
    cursor.execute("PRAGMA table_info(cryptocurrencies)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'logo_path' not in columns:
        print("Добавляю столбец logo_path в таблицу cryptocurrencies")
        cursor.execute("ALTER TABLE cryptocurrencies ADD COLUMN logo_path TEXT")
        conn.commit()
        print("Столбец logo_path успешно добавлен")
    else:
        print("Столбец logo_path уже существует")
    
    if 'updated_at' not in columns:
        print("Добавляю столбец updated_at в таблицу cryptocurrencies")
        # Вместо DEFAULT CURRENT_TIMESTAMP добавляем просто столбец
        cursor.execute("ALTER TABLE cryptocurrencies ADD COLUMN updated_at TIMESTAMP")
        # А затем выполняем UPDATE для установки значений
        cursor.execute("UPDATE cryptocurrencies SET updated_at = CURRENT_TIMESTAMP")
        conn.commit()
        print("Столбец updated_at успешно добавлен")
    else:
        print("Столбец updated_at уже существует")
    
    conn.close()
    print("Обновление схемы базы данных завершено")

if __name__ == "__main__":
    update_database_schema()
