"""
Message handlers for the Telegram bot.
This module contains handlers for different types of messages (text, photo, document).
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext
from config import MESSAGES

logger = logging.getLogger(__name__)

def handle_text(update: Update, context: CallbackContext) -> None:
    """
    Handle text messages from users.
    
    Args:
        update: The update object with information about the incoming message
        context: The context object for the callback
    """
    user = update.effective_user
    text = update.message.text
    logger.info(f"Received text message from user {user.id} ({user.full_name}): {text}")
    
    # Respond to the user with their message
    response = MESSAGES['text_received'].format(text)
    update.message.reply_text(response)


def handle_photo(update: Update, context: CallbackContext) -> None:
    """
    Handle photo messages from users.
    
    Args:
        update: The update object with information about the incoming message
        context: The context object for the callback
    """
    user = update.effective_user
    logger.info(f"Received photo from user {user.id} ({user.full_name})")
    
    # Get the photo with the highest resolution
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    # Log the photo file_id (could be used to retrieve the file later)
    logger.info(f"Photo file_id: {file_id}")
    
    # Respond to the user
    update.message.reply_text(MESSAGES['photo_received'])


def handle_document(update: Update, context: CallbackContext) -> None:
    """
    Handle document messages from users.
    
    Args:
        update: The update object with information about the incoming message
        context: The context object for the callback
    """
    user = update.effective_user
    document = update.message.document
    file_name = document.file_name
    
    logger.info(f"Received document from user {user.id} ({user.full_name}): {file_name}")
    
    # Log the document file_id (could be used to retrieve the file later)
    logger.info(f"Document file_id: {document.file_id}")
    
    # Respond to the user
    response = MESSAGES['document_received'].format(file_name)
    update.message.reply_text(response)
