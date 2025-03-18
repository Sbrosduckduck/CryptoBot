from telegram import Update
from telegram.ext import ContextTypes
from database import db
from crypto_utils import crypto_api
from config import ADMIN_IDS, SUPPORTED_CRYPTO
from logger import logger

# Admin commands
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get bot statistics - admin only"""
    logger.info(f"Получена команда admin_stats от пользователя {update.effective_user.id}")
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Get total users
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]

                # Get total transactions
                cursor.execute("SELECT COUNT(*) FROM transactions")
                total_transactions = cursor.fetchone()[0]

                stats_message = (
                    f"📊 Статистика бота:\n\n"
                    f"Всего пользователей: {total_users}\n"
                    f"Всего транзакций: {total_transactions}"
                )

                await update.message.reply_text(stats_message)
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text("Ошибка при получении статистики.")

# User commands
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple ping command for testing"""
    logger.info(f"Получена команда ping от пользователя {update.effective_user.id}")
    await update.message.reply_text("pong! 🏓")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - introduces the bot"""
    logger.info(f"Получена команда start от пользователя {update.effective_user.id}")
    user = update.effective_user
    db.add_user(
        user.id,
        user.username,
        user.first_name,
        user.last_name
    )

    welcome_message = (
        f"Привет {user.first_name}! 🚀\n\n"
        "Я ваш Крипто Ассистент. Вот что я умею:\n\n"
        "/price <crypto> - Получить текущую цену\n"
        "/wallet - Посмотреть ваши кошельки\n"
        "/add_wallet <crypto> <address> - Добавить новый кошелек\n"
        "/help - Показать все команды"
    )

    await update.message.reply_text(welcome_message)

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current price for cryptocurrency"""
    logger.info(f"Получена команда price от пользователя {update.effective_user.id}")
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите криптовалюту (например, /price BTC)")
        return

    crypto = context.args[0].upper()
    if crypto not in SUPPORTED_CRYPTO:
        await update.message.reply_text(f"Неподдерживаемая криптовалюта. Поддерживаемые: {', '.join(SUPPORTED_CRYPTO.keys())}")
        return

    price = crypto_api.get_price(crypto)
    if price:
        await update.message.reply_text(f"Текущая цена {crypto}: ${price:,.2f}")
    else:
        await update.message.reply_text("Ошибка при получении цены. Попробуйте позже.")

async def view_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user's wallets"""
    logger.info(f"Получена команда wallet от пользователя {update.effective_user.id}")
    user_id = update.effective_user.id
    wallets = db.get_user_wallets(user_id)

    if not wallets:
        await update.message.reply_text("У вас ещё нет кошельков. Используйте /add_wallet чтобы добавить.")
        return

    wallet_message = "Ваши кошельки:\n\n"
    for wallet in wallets:
        price = crypto_api.get_price(wallet['crypto'])
        usd_value = price * wallet['balance'] if price else 0
        wallet_message += (
            f"🔹 {wallet['crypto']}:\n"
            f"Адрес: {wallet['address']}\n"
            f"Баланс: {wallet['balance']} ({usd_value:,.2f} USD)\n\n"
        )

    await update.message.reply_text(wallet_message)

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new wallet"""
    logger.info(f"Получена команда add_wallet от пользователя {update.effective_user.id}")
    if len(context.args) != 2:
        await update.message.reply_text("Использование: /add_wallet <crypto> <address>")
        return

    crypto, address = context.args[0].upper(), context.args[1]

    if crypto not in SUPPORTED_CRYPTO:
        await update.message.reply_text(f"Неподдерживаемая криптовалюта. Поддерживаемые: {', '.join(SUPPORTED_CRYPTO.keys())}")
        return

    if not crypto_api.validate_address(crypto, address):
        await update.message.reply_text("Неверный формат адреса кошелька.")
        return

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO wallets (user_id, crypto_currency, address)
                    VALUES (?, ?, ?)
                ''', (update.effective_user.id, crypto, address))
                conn.commit()
                await update.message.reply_text(f"Кошелек для {crypto} успешно добавлен!")
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"Error adding wallet: {e}")
        await update.message.reply_text("Ошибка при добавлении кошелька. Попробуйте позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    logger.info(f"Получена команда help от пользователя {update.effective_user.id}")
    help_message = (
        "Доступные команды:\n\n"
        "📊 Информация о ценах:\n"
        "/price <crypto> - Получить текущую цену\n\n"
        "👛 Управление кошельками:\n"
        "/wallet - Посмотреть ваши кошельки\n"
        "/add_wallet <crypto> <address> - Добавить новый кошелек\n\n"
        "ℹ️ Другие команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать это сообщение\n\n"
        f"Поддерживаемые криптовалюты: {', '.join(SUPPORTED_CRYPTO.keys())}"
    )

    await update.message.reply_text(help_message)