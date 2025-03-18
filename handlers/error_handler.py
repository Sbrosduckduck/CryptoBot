"""
Error handler for the Telegram bot.
This module handles errors that occur during bot operation.
"""

import logging
import traceback
import html
from telegram import Update
from telegram.ext import CallbackContext
from config import MESSAGES

logger = logging.getLogger(__name__)

def error_handler(update: Update, context: CallbackContext) -> None:
    """
    Handle errors occurring in the dispatcher.
    Log the error and notify the user.
    
    Args:
        update: The update object with information about the incoming message
        context: The context object for the callback
    """
    # Log the error
    logger.error(f"Exception while handling an update: {context.error}")
    
    # traceback info
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    logger.error(f"Traceback: {tb_string}")
    
    # Notify the developer about the error (could be customized to send to a specific chat)
    error_message = f"An exception was raised while handling an update\n" \
                    f"<pre>{html.escape(tb_string)}</pre>"
    
    # If we can get chat_id from the update, notify the user about the error
    if update and update.effective_chat:
        # Send a simplified message to the user
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MESSAGES['error_occurred']
        )
    
    # Log that we've handled the error
    logger.info("Error handled and user notified if possible")
