"""
Command handlers for the Telegram bot.
This module contains handlers for bot commands like /start, /help, etc.
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext
from config import MESSAGES

logger = logging.getLogger(__name__)

def start_command(update: Update, context: CallbackContext) -> None:
    """
    Handle the /start command.
    Send a welcome message to the user.
    
    Args:
        update: The update object with information about the incoming message
        context: The context object for the callback
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.full_name}) started the bot")
    
    message = f"Привет, {user.first_name}! {MESSAGES['welcome']}"
    update.message.reply_text(message)


def help_command(update: Update, context: CallbackContext) -> None:
    """
    Handle the /help command.
    Send a help message with available commands to the user.
    
    Args:
        update: The update object with information about the incoming message
        context: The context object for the callback
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.full_name}) requested help")
    
    update.message.reply_text(MESSAGES['help'])
