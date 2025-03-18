import logging
import os
import signal
import socket
import sys
import time
from threading import Thread, Event, Lock
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackQueryHandler
)
from telegram.error import TelegramError, Conflict
from flask import Flask
from config import TOKEN
from database import init_db, get_db
from user_handlers import (
    start, register_start, first_name, last_name, middle_name,
    birth_date, email, phone, cancel, profile, deposit, withdraw,
    handle_button, FIRST_NAME, LAST_NAME, MIDDLE_NAME, BIRTH_DATE,
    EMAIL, PHONE, process_crypto_purchase_callback, buy_crypto_handler,
    process_crypto_sell_callback, show_graph
)
from admin_handlers import (
    admin_stats, admin_menu, show_users,
    edit_crypto_handler, view_transactions_handler,
    view_transactions_handler_message, add_crypto_handler,
    view_pending_transactions_handler,
    view_pending_transactions_handler_message,
    process_transaction_handler
)

# Инициализация логирования из нашего модуля logger
from logger import logger

# Настройка логирования для Flask
flask_logger = logging.getLogger('werkzeug')
flask_logger.setLevel(logging.INFO)

# Инициализация Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Глобальные флаги для корректного завершения
shutdown_event = Event()
instance_lock = Lock()
LOCK_FILE = "bot.lock"
SHUTDOWN_TIMEOUT = 10  # timeout in seconds

def is_port_in_use(port):
    """Проверяет, занят ли порт"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def create_lock_file():
    """Создает файл блокировки"""
    try:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Проверяем существование процесса
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)  # Даем процессу время на завершение
                    if os.path.exists(LOCK_FILE):
                        os.remove(LOCK_FILE)  # Удаляем старый лок-файл
                except ProcessLookupError:
                    # Процесс не существует, можно удалить файл
                    os.remove(LOCK_FILE)
            except (ValueError, OSError) as e:
                logger.error(f"Error handling existing lock file: {e}")
                os.remove(LOCK_FILE)  # В случае ошибки, удаляем файл

        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception as e:
        logger.error(f"Error creating lock file: {e}")
        return False

def remove_lock_file():
    """Удаляет файл блокировки"""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
                if pid == os.getpid():  # Удаляем только свой lock-файл
                    os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")

def cleanup_database():
    """Очищает незавершенные транзакции и закрывает соединения"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE transactions 
                SET status = 'cancelled' 
                WHERE status = 'pending'
            """)
            conn.commit()
    except Exception as e:
        logger.error(f"Error cleaning up database: {e}")

@app.route('/')
def home():
    return "Telegram bot is running"

def find_free_port(start_port=5000, max_attempts=10):
    """Ищет свободный порт"""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    raise RuntimeError("No free ports found")

def run_flask():
    """Запускает Flask сервер"""
    try:
        logger.info("Starting Flask server...")
        port = find_free_port(start_port=8080)  # Changed from 5000 to avoid conflicts
        logger.info(f"Flask server will run on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Error starting Flask server: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"Received signal {signum}")
    shutdown_event.set()

def error_handler(update, context):
    """Обработчик ошибок"""
    try:
        if isinstance(context.error, Conflict):
            logger.error("Bot instance conflict detected. Attempting to restart...")
            return

        error_msg = str(context.error)
        logger.error(f'Update "{update}" caused error "{error_msg}"')

        if update and update.effective_message:
            update.effective_message.reply_text(
                "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def cleanup():
    """Очистка ресурсов при завершении"""
    logger.info("Cleaning up resources...")
    cleanup_database()
    remove_lock_file()

def main():
    try:
        # Проверяем, не запущен ли уже бот
        if not create_lock_file():
            logger.error("Another instance is already running")
            sys.exit(1)

        # Регистрация обработчика сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Инициализация базы данных
        logger.info("Initializing database...")
        init_db()

        # Проверка наличия токена
        if not TOKEN:
            logger.error("Telegram bot token not found!")
            return

        # Создание updater и диспетчера
        logger.info("Creating Telegram bot updater...")
        updater = Updater(token=TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        # Регистрация обработчика для покупки и продажи криптовалюты
        logger.debug("Adding crypto buy/sell button handlers...")

        # Регистрируем обработчики с корректными паттернами
        buy_handler = CallbackQueryHandler(
            process_crypto_purchase_callback,
            pattern=r'^buy_|^buyamt_|^buyconfirm_|^buycancel$'
        )

        sell_handler = CallbackQueryHandler(
            process_crypto_sell_callback,
            pattern=r'^sell_|^sellamt_|^sellconfirm_|^sellcancel$'
        )

        # Добавляем обработчики в правильном порядке
        dispatcher.add_handler(buy_handler)
        dispatcher.add_handler(sell_handler)
        logger.info("Crypto handlers registered successfully")

        # Добавляем обработчик для отображения графиков
        chart_handler = CallbackQueryHandler(
            show_graph,
            pattern=r'^chart_'
        )
        dispatcher.add_handler(chart_handler)
        logger.info("Chart handler registered successfully")


        # Регистрация обработчика ошибок
        dispatcher.add_error_handler(error_handler)

        # Регистрация основных обработчиков команд
        logger.info("Registering command handlers...")
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("admin", admin_menu))
        dispatcher.add_handler(CommandHandler("stats", admin_stats))
        dispatcher.add_handler(CommandHandler("users", show_users))
        dispatcher.add_handler(CommandHandler("profile", profile))
        dispatcher.add_handler(CommandHandler("deposit", deposit))
        dispatcher.add_handler(CommandHandler("withdraw", withdraw))

        # Add the transaction handlers
        dispatcher.add_handler(view_transactions_handler)
        dispatcher.add_handler(view_transactions_handler_message)

        # Add handlers for pending transactions
        dispatcher.add_handler(view_pending_transactions_handler)
        dispatcher.add_handler(view_pending_transactions_handler_message)
        dispatcher.add_handler(process_transaction_handler)

        # Add crypto handlers from admin_handlers
        dispatcher.add_handler(add_crypto_handler)
        dispatcher.add_handler(edit_crypto_handler)

        # Обработчик регистрации
        logger.debug("Adding registration handler...")
        register_handler = ConversationHandler(
            entry_points=[CommandHandler("register", register_start)],
            states={
                FIRST_NAME: [MessageHandler(Filters.text & ~Filters.command, first_name)],
                LAST_NAME: [MessageHandler(Filters.text & ~Filters.command, last_name)],
                MIDDLE_NAME: [MessageHandler(Filters.text & ~Filters.command, middle_name)],
                BIRTH_DATE: [MessageHandler(Filters.text & ~Filters.command, birth_date)],
                EMAIL: [MessageHandler(Filters.text & ~Filters.command, email)],
                PHONE: [MessageHandler(Filters.text & ~Filters.command, phone)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            allow_reentry=True
        )
        dispatcher.add_handler(register_handler)

        # Обработчик кнопок (должен быть последним)
        logger.debug("Adding button handler...")
        dispatcher.add_handler(MessageHandler(
            Filters.text & ~Filters.command,
            handle_button
        ))

        # Запуск Flask в отдельном потоке
        logger.info("Starting Flask server in a separate thread...")
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Запуск бота
        logger.info("Starting bot polling...")
        updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query', 'chat_member'],
            timeout=30
        )
        logger.info("Bot started successfully!")

        # Ожидаем сигнала завершения
        shutdown_event.wait()

        # Корректное завершение
        logger.info("Stopping bot...")
        updater.stop()
        logger.info("Bot stopped successfully!")

    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        logger.exception("Full error details:")
    finally:
        cleanup()

if __name__ == '__main__':
    main()