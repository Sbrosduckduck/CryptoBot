from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler
from config import logger
# Определяем функцию format_help_message здесь
def format_help_message():
    """Format and return help message"""
    return (
        "📚 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Получить справку\n"
        "/register - Зарегистрироваться\n"
        "/profile - Посмотреть свой профиль\n"
        "/deposit <сумма> - Пополнить баланс\n"
        "/withdraw <сумма> - Вывести средства\n"
    )

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            f"👋 Hello, {update.effective_user.first_name}!\n"
            "I'm a bot created with python-telegram-bot. Use /help to see available commands."
        )
        logger.info(f"User {update.effective_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again later.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        help_text = format_help_message()
        await update.message.reply_text(help_text)
        logger.info(f"Help command used by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("Sorry, I couldn't process your request. Please try again later.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            f"You said: {update.message.text}\n"
            "Use /help to see available commands."
        )
        logger.debug(f"Received message from {update.effective_user.id}: {update.message.text}")
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        await update.message.reply_text("Sorry, I couldn't process your message. Please try again later.")

def register_handlers(dp):
    """Register all handlers to the dispatcher"""
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("help", cmd_help))
    # Add text handler last
    dp.add_handler(MessageHandler(None, handle_text))