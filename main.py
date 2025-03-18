import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, Application, CallbackQueryHandler
from commands import (
    start, help_command, get_price,
    view_wallet, add_wallet, admin_stats,
    ping  # Add ping import
)
from config import TOKEN
from logger import logger
from user_handlers import process_crypto_purchase_callback

def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")

async def main():
    """Initialize and start the bot"""
    # Enable debug logging for python-telegram-bot
    logging.getLogger('telegram').setLevel(logging.DEBUG)
    logging.getLogger('httpx').setLevel(logging.DEBUG)

    # Create application with token
    application = ApplicationBuilder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", get_price))
    application.add_handler(CommandHandler("wallet", view_wallet))
    application.add_handler(CommandHandler("add_wallet", add_wallet))
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("ping", ping))  # Add ping handler

    # Add handler for crypto purchase and sell callbacks
    application.add_handler(CallbackQueryHandler(process_crypto_purchase_callback, pattern='^buy_|^buyamt_|^buyconfirm_|^buycancel$|^sell_'))
    
    # Add handler for crypto sell process
    from user_handlers import process_crypto_sell_callback
    application.add_handler(CallbackQueryHandler(process_crypto_sell_callback, pattern='^sellamt_|^sellconfirm_|^sellcancel$'))

    # Add error handler
    application.add_error_handler(error_handler)

    logger.info("Starting bot polling...")

    # Start polling
    await application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")