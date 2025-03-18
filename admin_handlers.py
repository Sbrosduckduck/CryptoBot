import logging
import os
import io
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from database import (
    get_db, get_all_cryptos, get_user, add_crypto,
    update_crypto, validate_crypto_symbol, get_crypto_by_id,
    get_pending_transactions, update_transaction_status, update_user_balance
)
from utils import (
    is_admin, format_money, format_crypto_amount
)
from config import ADMIN_EMAIL

# Configuration constants
logger = logging.getLogger(__name__)

# Admin menu buttons configuration

# Conversation handler states
ADD_CRYPTO_NAME, ADD_CRYPTO_SYMBOL, ADD_CRYPTO_RATE, ADD_CRYPTO_SUPPLY = range(4)
EDIT_CRYPTO_SELECT, EDIT_CRYPTO_ACTION, EDIT_CRYPTO_RATE, EDIT_CRYPTO_SUPPLY = range(4, 8)

def check_admin(func):
    """Декоратор для проверки прав администратора"""
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        logger.info(f"Admin check for user {user_id}")

        try:
            # Получаем информацию о пользователе
            user = get_user(user_id)
            logger.debug(f"User data: {user}")

            # Проверяем права администратора
            if not is_admin(user_id):
                logger.warning(f"Unauthorized admin access attempt from user {user_id}")
                update.message.reply_text("У вас нет прав администратора.")
                return

            logger.info(f"Admin access granted for user {user_id}")
            return func(update, context)

        except Exception as e:
            logger.error(f"Error in admin check: {str(e)}")
            update.message.reply_text("Произошла ошибка при проверке прав администратора.")
            return
    return wrapper

@check_admin
def admin_stats(update: Update, context: CallbackContext):
    """Shows detailed system statistics for admins"""
    try:
        logger.info(f"Starting admin_stats for user {update.effective_user.id}")

        logger.info("Admin check passed, getting database connection")

        with get_db() as conn:
            cursor = conn.cursor()

            logger.info("Getting user statistics")
            # Получаем статистику пользователей
            user_query = '''
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as new_today,
                    COALESCE(SUM(balance), 0) as total_balance,
                    COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as active_users
                FROM users
            '''
            logger.debug(f"Executing user query: {user_query}")
            cursor.execute(user_query)
            user_stats = cursor.fetchone()
            logger.debug(f"User stats: {user_stats}")

            logger.info("Getting trading statistics")
            # Получаем статистику транзакций
            trade_query = '''
                SELECT 
                    COUNT(*) as total_trades,
                    COALESCE(SUM(amount), 0) as total_volume_rub,
                    COUNT(DISTINCT user_id) as unique_traders
                FROM transactions
                WHERE created_at >= datetime('now', '-30 days')
            '''
            logger.debug(f"Executing trade query: {trade_query}")
            cursor.execute(trade_query)
            trade_stats = cursor.fetchone()
            logger.debug(f"Trade stats: {trade_stats}")

            logger.info("Getting cryptocurrency distribution")
            # Получаем распределение криптовалют
            crypto_query = '''
                SELECT c.name, c.symbol, COUNT(p.crypto_id) as trade_count, 
                       COALESCE(SUM(p.amount * c.rate), 0) as volume_rub
                FROM cryptocurrencies c
                LEFT JOIN portfolios p ON c.id = p.crypto_id
                GROUP BY c.id
                ORDER BY volume_rub DESC
                LIMIT 5
            '''
            logger.debug(f"Executing crypto query: {crypto_query}")
            cursor.execute(crypto_query)
            top_cryptos = cursor.fetchall()
            logger.debug(f"Top cryptos: {top_cryptos}")

            logger.info("Getting user growth data")
            # Генерируем график роста пользователей
            growth_query = '''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM users
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            '''
            logger.debug(f"Executing growth query: {growth_query}")
            cursor.execute(growth_query)
            growth_data = cursor.fetchall()
            logger.debug(f"Growth data: {growth_data}")

            try:
                logger.info("Creating growth chart")
                # Создаем график
                plt.figure(figsize=(10, 5))

                if growth_data:
                    logger.debug("Processing growth data for chart")
                    dates = [row[0] for row in growth_data]
                    counts = [row[1] for row in growth_data]
                    logger.debug(f"Chart data - dates: {dates}, counts: {counts}")

                    plt.plot(dates, counts, marker='o')
                    plt.title('Рост пользователей за последние 7 дней')
                    plt.xlabel('Дата')
                    plt.ylabel('Новые пользователи')
                    plt.grid(True)
                    plt.xticks(rotation=45)
                else:
                    logger.warning("No growth data available for chart")
                    plt.text(0.5, 0.5, 'Нет данных о регистрациях', 
                            horizontalalignment='center',
                            verticalalignment='center')

                # Создаем директорию для графиков, если её нет
                os.makedirs('static', exist_ok=True)

                # Сохраняем график
                growth_chart_path = 'static/user_growth.png'
                logger.debug(f"Saving chart to {growth_chart_path}")
                plt.savefig(growth_chart_path, bbox_inches='tight')
                plt.close()
                logger.info(f"Chart saved to {growth_chart_path}")

            except Exception as chart_error:
                logger.error(f"Error creating chart: {str(chart_error)}")
                logger.exception("Full chart error details:")
                plt.close()  # Закрываем график в случае ошибки

            logger.info("Formatting statistics message")
            # Форматируем сообщение со статистикой
            stats_message = (
                "📊 *Системная статистика*\n\n"
                "*👥 Пользователи:*\n"
            )

            if user_stats:
                stats_message += (
                    f"• Всего: {user_stats[0]:,}\n"
                    f"• Активных (7 дней): {user_stats[3]:,}\n"
                    f"• Новых сегодня: {user_stats[1]:,}\n"
                    f"• Общий баланс: {format_money(user_stats[2])}\n\n"
                )
            else:
                stats_message += "• Нет данных о пользователях\n\n"

            stats_message += "*💹 Торговые показатели (30 дней):*\n"

            if trade_stats:
                stats_message += (
                    f"• Объем торгов: {format_money(trade_stats[1])}\n"
                    f"• Количество сделок: {trade_stats[0]:,}\n"
                    f"• Уникальных трейдеров: {trade_stats[2]:,}\n\n"
                )
            else:
                stats_message += "• Нет данных о торгах\n\n"

            stats_message += "*🔝 Топ криптовалют по объему:*\n"

            if top_cryptos:
                for crypto in top_cryptos:
                    stats_message += (
                        f"• {crypto[0]} ({crypto[1]})\n"
                        f"  Объем: {format_money(crypto[3])}\n"
                        f"  Сделок: {crypto[2]:,}\n"
                    )
            else:
                stats_message += "• Нет данных о криптовалютах\n"

            logger.info("Sending statistics message")
            logger.debug(f"Stats message content: {stats_message}")
            # Отправляем статистику
            update.message.reply_text(stats_message, parse_mode='Markdown')

            # Отправляем график, если он был создан
            if os.path.exists(growth_chart_path):
                logger.info("Sending growth chart")
                try:
                    with open(growth_chart_path, 'rb') as photo:
                        update.message.reply_photo(
                            photo=photo,
                            caption="📈 График роста пользователей за последние 7 дней"
                        )
                    os.remove(growth_chart_path)
                    logger.info("Growth chart sent and removed")
                except Exception as photo_error:
                    logger.error(f"Error sending photo: {str(photo_error)}")
                    logger.exception("Full photo error details:")
            else:
                logger.warning(f"Growth chart file not found at {growth_chart_path}")

    except Exception as e:
        logger.error(f"Error generating admin statistics: {str(e)}")
        logger.exception("Full error details:")
        update.message.reply_text(
            "Произошла ошибка при формировании статистики. "
            "Попробуйте позже или обратитесь к разработчику."
        )
    finally:
        plt.close('all')  # Закрываем все графики

def get_admin_buttons():
    """Returns admin buttons with pending count"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'pending'")
        pending_count = cursor.fetchone()['count']

    return [
        ["📊 Статистика", "👥 Пользователи"],
        ["💰 Транзакции", f"📥 Заявки ({pending_count})"],
        ["➕ Добавить крипту", "✏️ Редактировать крипту"],
        ["↩️ Обычное меню"]
    ]

@check_admin
def admin_menu(update: Update, context: CallbackContext):
    """Показывает админ-меню"""
    logger.info(f"Admin menu accessed by user {update.effective_user.id}")
    keyboard = ReplyKeyboardMarkup(get_admin_buttons(), resize_keyboard=True)
    update.message.reply_text(
        "Админ-панель. Выберите действие:\n\n"
        "📊 Статистика - просмотр детальной статистики системы\n"
        "👥 Пользователи - управление пользователями\n"
        "💰 Транзакции - просмотр запросов на ввод/вывод средств\n"
        "📥 Заявки - просмотр активных заявок на пополнение/вывод средств\n"
        "➕ Добавить крипту - добавление новой криптовалюты\n"
        "✏️ Редактировать крипту - изменение параметров криптовалюты\n"
        "↩️ Обычное меню - вернуться в обычное меню",
        reply_markup=keyboard
    )
    logger.debug("Admin menu displayed successfully")

@check_admin
def add_crypto_command(update: Update, context: CallbackContext):
    """Начинает процесс добавления новой криптовалюты"""
    logger.info(f"Add crypto process started by admin {update.effective_user.id}")

    try:
        update.message.reply_text(
            "Добавление новой криптовалюты.\n\n"
            "Введите название криптовалюты:"
        )
        logger.info("Admin prompted for crypto name")
        return ADD_CRYPTO_NAME
    except Exception as e:
        logger.error(f"Error in add_crypto_command: {e}")
        logger.exception("Full error details:")
        update.message.reply_text("Произошла ошибка при запуске процесса добавления криптовалюты.")
        return ConversationHandler.END

@check_admin
def edit_crypto_command(update: Update, context: CallbackContext):
    """Начинает процесс редактирования криптовалюты"""
    logger.info(f"Edit crypto process started by admin {update.effective_user.id}")
    cryptos = get_all_cryptos(include_private=True)

    if not cryptos:
        logger.warning("No cryptocurrencies available for editing")
        update.message.reply_text("Нет доступных криптовалют для редактирования.")
        return ConversationHandler.END

    keyboard = []
    for crypto in cryptos:
        button = InlineKeyboardButton(
            f"{crypto['name']} ({crypto['symbol']}) - {format_money(crypto['rate'])}",
            callback_data=f"edit_crypto_{crypto['id']}"
        )
        keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Выберите криптовалюту для редактирования:",
        reply_markup=reply_markup
    )
    logger.debug(f"Edit crypto menu displayed with {len(cryptos)} options")
    return EDIT_CRYPTO_SELECT

@check_admin
def show_users(update: Update, context: CallbackContext):
    """Показывает список пользователей"""
    logger.info(f"User list requested by admin {update.effective_user.id}")

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            users = cursor.fetchall()

        if not users:
            logger.warning("No users found in database")
            update.message.reply_text("Пользователей не найдено.")
            return

        message = "👥 Список пользователей:\n\n"
        for user in users:
            user_name = f"{user['first_name']} {user['last_name']}"
            user_link = f"[{user_name}](tg://user?id={user['user_id']})"
            phone = user['phone'] if user['phone'] else 'Не указан'
            balance = format_money(user['balance']) if user['balance'] else '0₽'
            message += f"• {user_link}\n📱 {phone}\n💰 Баланс: {balance}\n\n"

        update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"User list displayed: {len(users)} users")

    except Exception as e:
        logger.error(f"Error showing users: {str(e)}")
        update.message.reply_text("Произошла ошибка при получении списка пользователей.")


# Add new function to view transactions
@check_admin
def view_transactions(update: Update, context: CallbackContext):
    """Показывает список транзакций пользователей"""
    logger.info(f"Transactions view accessed by admin {update.effective_user.id}")

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Получаем все транзакции с информацией о пользователях
            cursor.execute('''
                SELECT t.*, u.first_name, u.last_name, u.email
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                ORDER BY t.created_at DESC
                LIMIT 20
            ''')
            transactions = cursor.fetchall()

            logger.info(f"Retrieved {len(transactions) if transactions else 0} transactions from database")

        if not transactions:
            logger.info("No transactions found in database")
            update.message.reply_text("Транзакций пока нет.")
            return

        message = "💰 Последние транзакции:\n\n"
        for tx in transactions:
            try:
                # Форматируем статус
                status_emoji = {
                    'pending': '⏳',
                    'completed': '✅',
                    'rejected': '❌'
                }.get(tx['status'], '❓')

                # Форматируем тип операции
                type_text = 'пополнение' if tx['type'] == 'deposit' else 'вывод'

                # Безопасное получение временной метки
                try:
                    if isinstance(tx['created_at'], str):
                        created_at = datetime.strptime(tx['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
                    else:
                        created_at = datetime.fromtimestamp(float(tx['created_at'])).strftime('%d.%m.%Y %H:%M')
                except (TypeError, ValueError) as e:
                    logger.error(f"Error formatting timestamp for transaction {tx['id']}: {e}")
                    created_at = tx['created_at'] if tx['created_at'] else "Дата неизвестна"

                # Форматируем сообщение для каждой транзакции
                message += (
                    f"{status_emoji} {type_text.capitalize()}\n"
                    f"ID: #{tx['unique_id']}\n"
                    f"От: {tx['first_name']} {tx['last_name']} ({tx['email']})\n"
                    f"Сумма: {format_money(tx['amount'])}\n"
                    f"Статус: {tx['status']}\n"
                    f"Создано: {created_at}\n\n"
                )

                # Если сообщение слишком длинное, отправляем часть и начинаем новое
                if len(message) > 3500:  # Telegram limit is 4096
                    update.message.reply_text(message)
                    message = "Продолжение списка транзакций:\n\n"

            except Exception as e:
                logger.error(f"Error processing transaction {tx['id']}: {e}")
                continue

        # Отправляем оставшиеся транзакции
        if message:
            update.message.reply_text(message)
            logger.info("Successfully sent transactions list to admin")

    except Exception as e:
        logger.error(f"Error showing transactions: {str(e)}")
        logger.exception("Full error details:")
        update.message.reply_text("Произошла ошибка при получении списка транзакций.")

# Модифицируем функцию view_pending_transactions для добавления логирования
@check_admin
def view_pending_transactions(update: Update, context: CallbackContext):
    """Показывает список активных заявок на пополнение/вывод средств"""
    logger.info(f"Pending transactions view accessed by admin {update.effective_user.id}")

    try:
        # Получаем все активные заявки
        pending_transactions = get_pending_transactions()
        logger.debug(f"Found {len(pending_transactions)} pending transactions")

        if not pending_transactions:
            logger.info("No pending transactions found")
            update.message.reply_text("Активных заявок нет.")
            return

        for tx in pending_transactions:
            logger.debug(f"Processing transaction {tx['id']}: {tx['type']} for {tx['amount']}")
            # Форматируем сообщение для каждой заявки
            message = (
                f"{'📥' if tx['type'] == 'deposit' else '📤'} "
                f"{'Пополнение' if tx['type'] == 'deposit' else 'Вывод'}\n"
                f"От: {tx['first_name']} {tx['last_name']}\n"
                f"Email: {tx['email']}\n"
                f"Сумма: {format_money(tx['amount'])}\n"
                f"Создано: {tx['created_at']}\n"
            )

            # Создаем клавиатуру с кнопками подтверждения/отклонения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{tx['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{tx['id']}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем сообщение с кнопками
            update.message.reply_text(message, reply_markup=reply_markup)
            logger.debug(f"Sent message for transaction {tx['id']}")

    except Exception as e:
        logger.error(f"Error showing pending transactions: {str(e)}")
        logger.exception("Full error details:")
        update.message.reply_text("Произошла ошибка при получении списка заявок.")

@check_admin
def process_transaction(update: Update, context: CallbackContext):
    """Обрабатывает подтверждение или отклонение заявки"""
    query = update.callback_query
    query.answer()

    logger.info(f"Processing transaction callback: {query.data}")

    try:
        # Получаем действие и ID транзакции
        action, tx_id = query.data.split('_')
        tx_id = int(tx_id)
        logger.info(f"Processing transaction {tx_id} with action {action}")

        # Получаем информацию о транзакции
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, u.user_id, u.balance, u.first_name, u.last_name 
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.id = ? AND t.status = ?
            """, (tx_id, 'pending'))
            tx = cursor.fetchone()

        if not tx:
            logger.warning(f"Transaction {tx_id} not found or already processed")
            query.edit_message_text("Заявка не найдена или уже обработана.")
            return

        logger.debug(f"Found transaction: {dict(tx)}")
        user_id = tx['user_id']
        amount = tx['amount']
        tx_type = tx['type']

        if action == 'approve':
            # Process approval
            logger.info(f"Approving transaction {tx_id}")
            success = update_transaction_status(tx_id, 'completed')

            if success:
                new_balance = tx['balance'] + amount if tx_type == 'deposit' else tx['balance'] - amount
                if update_user_balance(user_id, new_balance):
                    logger.info(f"Successfully processed {tx_type} for user {user_id}, new balance: {new_balance}")

                    # Notify user
                    context.bot.send_message(
                        user_id,
                        f"✅ Ваша заявка на {'пополнение' if tx_type == 'deposit' else 'вывод'} "
                        f"средств на сумму {format_money(amount)} одобрена.\n"
                        f"Ваш новый баланс: {format_money(new_balance)}"
                    )

                    query.edit_message_text(
                        f"✅ Заявка одобрена\n"
                        f"Пользователь: {tx['first_name']} {tx['last_name']}\n"
                        f"Сумма: {format_money(amount)}\n"
                        f"Новый баланс: {format_money(new_balance)}"
                    )
                else:
                    logger.error(f"Failed to update balance for user {user_id}")
                    query.edit_message_text("❌ Ошибка при обновлении баланса пользователя.")
            else:
                logger.error(f"Failed to update transaction status for tx_id {tx_id}")
                query.edit_message_text("❌ Ошибка при обновлении статуса транзакции.")

        elif action == 'reject':
            logger.info(f"Rejecting transaction {tx_id}")
            if update_transaction_status(tx_id, 'rejected'):
                logger.info(f"Successfully rejected transaction {tx_id}")

                # Notify user
                context.bot.send_message(
                    user_id,
                    f"❌ Ваша заявка на {'пополнение' if tx_type == 'deposit' else 'вывод'} "
                    f"средств на сумму {format_money(amount)} отклонена.\n"
                    f"Для получения дополнительной информации свяжитесь с администратором."
                )

                query.edit_message_text(
                    f"❌ Заявка отклонена\n"
                    f"Пользователь: {tx['first_name']} {tx['last_name']}\n"
                    f"Сумма: {format_money(amount)}"
                )
            else:
                logger.error(f"Failed to reject transaction {tx_id}")
                query.edit_message_text("❌ Ошибка при обновлении статуса транзакции.")

    except Exception as e:
        logger.error(f"Error processing transaction: {str(e)}")
        logger.exception("Full error details:")
        query.edit_message_text("❌ Произошла ошибка при обработке заявки.")

# State definitions for conversation handlers
ADD_CRYPTO_NAME, ADD_CRYPTO_SYMBOL, ADD_CRYPTO_RATE, ADD_CRYPTO_SUPPLY = range(10, 14)
EDIT_CRYPTO_SELECT, EDIT_CRYPTO_RATE, EDIT_CRYPTO_SUPPLY = range(20, 23)

# Helper functions
def cancel(update: Update, context: CallbackContext):
    """Отменяет текущее действие"""
    update.message.reply_text("Действие отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# Add Crypto conversation handlers

def add_crypto_name(update: Update, context: CallbackContext):
    crypto_name = update.message.text

    # Проверяем уникальность названия
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM cryptocurrencies WHERE name = ?", (crypto_name,))
        existing_name = cursor.fetchone()

    if existing_name:
        update.message.reply_text(
            f"Криптовалюта с названием '{crypto_name}' уже существует. Пожалуйста, введите другое название:"
        )
        return ADD_CRYPTO_NAME

    context.user_data['crypto_name'] = crypto_name
    update.message.reply_text(
        "Введите символ криптовалюты (формат: 3 заглавные + 1 строчная буква, например: BTCd):"
    )
    return ADD_CRYPTO_SYMBOL

def add_crypto_symbol(update: Update, context: CallbackContext):
    symbol = update.message.text
    if not validate_crypto_symbol(symbol):
        update.message.reply_text(
            "Неверный формат символа. Должно быть 3 заглавные и 1 строчная буква (например: BTCd). Попробуйте снова:"
        )
        return ADD_CRYPTO_SYMBOL

    # Проверяем уникальность символа
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM cryptocurrencies WHERE symbol = ?", (symbol,))
        existing_symbol = cursor.fetchone()

    if existing_symbol:
        update.message.reply_text(
            f"Символ {symbol} уже используется. Пожалуйста, введите другой символ:"
        )
        return ADD_CRYPTO_SYMBOL

    context.user_data['crypto_symbol'] = symbol
    update.message.reply_text("Введите курс криптовалюты в рублях:")
    return ADD_CRYPTO_RATE

def add_crypto_rate(update: Update, context: CallbackContext):
    try:
        rate = float(update.message.text.replace(',', '.'))
        if rate <= 0:
            raise ValueError("Курс должен быть положительным числом")
        context.user_data['crypto_rate'] = rate

        # Отправляем сообщение и возвращаем следующее состояние
        update.message.reply_text("Введите общее количество монет:")
        return ADD_CRYPTO_SUPPLY
    except ValueError:
        update.message.reply_text("Неверный формат курса. Введите положительное число:")
        return ADD_CRYPTO_RATE

def add_crypto_supply(update: Update, context: CallbackContext):
    try:
        supply = float(update.message.text.replace(',', '.'))
        if supply <= 0:
            raise ValueError("Количество должно быть положительным числом")
        context.user_data['crypto_supply'] = supply
    except ValueError:
        update.message.reply_text("Неверный формат количества. Введите положительное число:")
        return ADD_CRYPTO_SUPPLY

    try:
        add_crypto(
            name=context.user_data['crypto_name'],
            symbol=context.user_data['crypto_symbol'],
            rate=context.user_data['crypto_rate'],
            total_supply=context.user_data['crypto_supply']
        )

        update.message.reply_text(
            f"Криптовалюта {context.user_data['crypto_name']} ({context.user_data['crypto_symbol']}) успешно добавлена!"
        )
    except Exception as e:
        update.message.reply_text(f"Ошибка при добавлении криптовалюты: {str(e)}")

    # Очищаем данные
    context.user_data.clear()
    return ConversationHandler.END

# Edit Crypto conversation handlers

def edit_crypto_select(update: Update, context: CallbackContext):
    """Обрабатывает выбор криптовалюты для редактирования"""
    query = update.callback_query
    query.answer()

    try:
        crypto_id = int(query.data.split("_")[-1])
        crypto = get_crypto_by_id(crypto_id, include_private=True)

        if not crypto:
            query.edit_message_text("Криптовалюта не найдена.")
            return ConversationHandler.END

        # Сохраняем данные о криптовалюте
        context.user_data['crypto_id'] = crypto_id
        context.user_data['crypto_name'] = crypto.get('name', '')
        context.user_data['crypto_symbol'] = crypto.get('symbol', '')

        keyboard = [
            [InlineKeyboardButton("Изменить курс", callback_data="edit_rate")],
            [InlineKeyboardButton("Изменить количество", callback_data="edit_supply")],
            [InlineKeyboardButton("Отмена", callback_data="cancel_edit")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = (
            f"Редактирование {crypto.get('name', '')} ({crypto.get('symbol', '')})\n\n"
            f"Текущий курс: {format_money(crypto.get('rate', 0))}\n"
            f"Общее количество: {format_crypto_amount(crypto.get('total_supply', 0))}\n"
            f"Доступное количество: {format_crypto_amount(crypto.get('available_supply', 0))}\n\n"
            "Выберите действие:"
        )

        query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup
        )

        return EDIT_CRYPTO_SELECT

    except Exception as e:
        logger.error(f"Error in edit_crypto_select: {str(e)}")
        query.edit_message_text("Произошла ошибка при выборе криптовалюты.")
        return ConversationHandler.END

def edit_crypto_action(update: Update, context: CallbackContext):
    """Обрабатывает выбор действия с криптовалютой"""
    query = update.callback_query
    query.answer()

    try:
        if query.data == "cancel_edit":
            query.edit_message_text("Редактирование отменено.")
            return ConversationHandler.END

        crypto = get_crypto_by_id(context.user_data.get('crypto_id'), include_private=True)
        if not crypto:
            query.edit_message_text("Ошибка: криптовалюта не найдена.")
            return ConversationHandler.END

        if query.data == "edit_rate":
            message_text = (
                f"Редактирование курса для {context.user_data.get('crypto_name', '')} "
                f"({context.user_data.get('crypto_symbol', '')})\n\n"
                f"Текущий курс: {format_money(crypto.get('rate', 0))}\n\n"
                "Введите новый курс (например: 100.50):"
            )
            query.edit_message_text(message_text)
            return EDIT_CRYPTO_RATE

        if query.data == "edit_supply":
            message_text = (
                f"Редактирование количества монет для {context.user_data.get('crypto_name', '')} "
                f"({context.user_data.get('crypto_symbol', '')})\n\n"
                f"Текущее количество: {format_crypto_amount(crypto.get('total_supply', 0))}\n\n"
                "Введите новое количество монет (например: 1000000):"
            )
            query.edit_message_text(message_text)
            return EDIT_CRYPTO_SUPPLY

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in edit_crypto_action: {str(e)}")
        query.edit_message_text("Произошла ошибка при выборе действия.")
        return ConversationHandler.END

def edit_crypto_rate(update: Update, context: CallbackContext):
    """Обновляет курс криптовалюты"""
    try:
        rate = float(update.message.text.replace(',', '.'))
        if rate <= 0:
            update.message.reply_text("Курс должен быть положительным числом.")
            return EDIT_CRYPTO_RATE

        crypto_id = context.user_data.get('crypto_id')
        if not crypto_id:
            update.message.reply_text("Ошибка: не найден ID криптовалюты.")
            return ConversationHandler.END

        # Get current crypto info
        crypto = get_crypto_by_id(crypto_id, include_private=True)
        if not crypto:
            update.message.reply_text("Ошибка: криптовалюта не найдена.")
            return ConversationHandler.END

        # Update the rate
        logger.info(f"Updating rate for crypto {crypto_id} to {rate}")
        success = update_crypto(
            crypto_id=crypto_id,
            rate=rate,  # Pass rate directly as float
            total_supply=crypto.get('total_supply'),  # Preserve existing supply
            available_supply=crypto.get('available_supply', 0)  # Default to 0 if None
        )

        if success:
            update.message.reply_text(
                f"Курс успешно обновлен!\n"
                f"Новый курс: {format_money(rate)}"
            )
        else:
            update.message.reply_text("Ошибка при обновлении курса.")

        return ConversationHandler.END

    except ValueError:
        update.message.reply_text("Неверный формат числа. Введите корректное число:")
        return EDIT_CRYPTO_RATE
    except Exception as e:
        logger.error(f"Error in edit_crypto_rate: {str(e)}")
        update.message.reply_text("Произошла ошибка при обновлении курса.")
        return ConversationHandler.END

def edit_crypto_supply(update: Update, context: CallbackContext):
    """Обновляет количество монет криптовалюты"""
    try:
        supply = float(update.message.text.replace(',', '.'))
        if supply <= 0:
            update.message.reply_text("Количество должно быть положительным числом.")
            return EDIT_CRYPTO_SUPPLY

        crypto_id = context.user_data.get('crypto_id')
        if not crypto_id:
            update.message.reply_text("Ошибка: не найден ID криптовалюты.")
            return ConversationHandler.END

        # Get current crypto info
        crypto = get_crypto_by_id(crypto_id, include_private=True)
        if not crypto:
            update.message.reply_text("Ошибка: криптовалюта не найдена.")
            return ConversationHandler.END

        current_rate = crypto.get('rate', 0)
        if current_rate is None:
            current_rate = 0

        # Update with new supply
        logger.info(f"Updating supply for crypto {crypto_id} to {supply}")
        success = update_crypto(
            crypto_id=crypto_id,
            rate=current_rate,
            total_supply=supply,
            available_supply=supply  # Set available supply equal to total supply
        )

        if success:
            update.message.reply_text(
                f"Количество монет успешно обновлено!\n"
                f"Новое количество: {format_crypto_amount(supply)}"
            )
        else:
            update.message.reply_text("Ошибка при обновлении количества монет.")

        return ConversationHandler.END

    except ValueError:
        update.message.reply_text("Неверный формат числа. Введите корректное число:")
        return EDIT_CRYPTO_SUPPLY
    except Exception as e:
        logger.error(f"Error in edit_crypto_supply: {str(e)}")
        update.message.reply_text("Произошла ошибка при обновлении количества монет.")
        return ConversationHandler.END

def update_crypto_with_history(crypto_id, rate, total_supply=None, available_supply=None):
    """Обновляет параметры криптовалюты и сохраняет историю изменений"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Получаем текущие значения
            cursor.execute("""
                SELECT rate, total_supply, available_supply
                FROM cryptocurrencies
                WHERE id = ?
            """, (crypto_id,))
            current = cursor.fetchone()

            if not current:
                return False

            # Обновляем криптовалюту
            cursor.execute("""
                UPDATE cryptocurrencies
                SET rate = ?,
                    total_supply = ?,
                    available_supply = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (
                rate if rate is not None else current['rate'],
                total_supply if total_supply is not None else current['total_supply'],
                available_supply if available_supply is not None else current['available_supply'],
                crypto_id
            ))

            # Сохраняем историю изменений
            cursor.execute("""
                INSERT INTO crypto_history (
                    crypto_id, old_rate, new_rate,
                    old_total_supply, new_total_supply,
                    old_available_supply, new_available_supply,
                    change_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                crypto_id,
                current['rate'], rate if rate is not None else current['rate'],
                current['total_supply'], total_supply if total_supply is not None else current['total_supply'],
                current['available_supply'], available_supply if available_supply is not None else current['available_supply']
            ))

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"Error updating crypto with history: {str(e)}")
        return False

# Define conversation handlers after all functions are defined
edit_crypto_handler = ConversationHandler(
    entry_points=[CommandHandler("edit_crypto", edit_crypto_command),
                  MessageHandler(Filters.regex(r"^✏️ Редактировать крипту$"), edit_crypto_command)],
    states={
        EDIT_CRYPTO_SELECT: [
            CallbackQueryHandler(edit_crypto_select, pattern=r"^edit_crypto_\d+$"),
            CallbackQueryHandler(edit_crypto_action, pattern=r"^edit_(rate|supply|cancel_edit)$")
        ],
        EDIT_CRYPTO_RATE: [MessageHandler(Filters.text & ~Filters.command, edit_crypto_rate)],
        EDIT_CRYPTO_SUPPLY: [MessageHandler(Filters.text & ~Filters.command, edit_crypto_supply)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True
)

add_crypto_handler = ConversationHandler(
    entry_points=[
        CommandHandler('add_crypto', add_crypto_command),
        MessageHandler(Filters.regex(r'^➕ Добавить крипту$'), add_crypto_command)
    ],
    states={
        ADD_CRYPTO_NAME: [MessageHandler(Filters.text & ~Filters.command, add_crypto_name)],
        ADD_CRYPTO_SYMBOL: [MessageHandler(Filters.text & ~Filters.command, add_crypto_symbol)],
        ADD_CRYPTO_RATE: [MessageHandler(Filters.text & ~Filters.command, add_crypto_rate)],
        ADD_CRYPTO_SUPPLY: [MessageHandler(Filters.text & ~Filters.command, add_crypto_supply)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)
view_transactions_handler = CommandHandler('view_transactions', view_transactions)
view_transactions_handler_message = MessageHandler(Filters.regex(r'^💰 Транзакции$'), view_transactions)

# Добавляем новые обработчики в конец файла
view_pending_transactions_handler = CommandHandler('pending_transactions', view_pending_transactions)
view_pending_transactions_handler_message = MessageHandler(
    Filters.regex(r'^📥 Заявки \(\d+\)$|^📥 Заявки$'), 
    view_pending_transactions
)
process_transaction_handler = CallbackQueryHandler(
    process_transaction,
    pattern=r'^(approve|reject)_\d+$'
)

# Добавляем новую кнопку в админ-меню