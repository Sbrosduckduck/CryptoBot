from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Tuple, Dict

from config import SUPPORTED_CRYPTOS

# Main menu keyboard
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Create main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Add buttons in rows
    keyboard.row(
        KeyboardButton("💰 Prices"),
        KeyboardButton("📊 Portfolio")
    )
    keyboard.row(
        KeyboardButton("💵 Buy"),
        KeyboardButton("💸 Sell")
    )
    keyboard.row(
        KeyboardButton("📜 History"),
        KeyboardButton("👤 Profile")
    )
    keyboard.row(
        KeyboardButton("ℹ️ Help")
    )
    
    return keyboard

# Admin menu keyboard
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Create admin menu keyboard."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Add buttons in rows
    keyboard.row(
        KeyboardButton("📊 Statistics"),
        KeyboardButton("👥 Users")
    )
    keyboard.row(
        KeyboardButton("💹 Transactions"),
        KeyboardButton("📣 Broadcast")
    )
    keyboard.row(
        KeyboardButton("🔙 Back to User Menu")
    )
    
    return keyboard

# Registration keyboard
def get_registration_keyboard() -> ReplyKeyboardMarkup:
    """Create registration keyboard."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📝 Register"))
    keyboard.add(KeyboardButton("❌ Cancel"))
    
    return keyboard

# Cancel keyboard
def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Create cancel keyboard."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Cancel"))
    
    return keyboard

# Back keyboard
def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Create back keyboard."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Back"))
    
    return keyboard

# Confirmation keyboard
def get_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """Create confirmation keyboard."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton("✅ Confirm"),
        KeyboardButton("❌ Cancel")
    )
    
    return keyboard

# Cryptocurrency selection inline keyboard
def get_crypto_inline_keyboard() -> InlineKeyboardMarkup:
    """Create cryptocurrency selection inline keyboard."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Add buttons for each cryptocurrency
    buttons = []
    for crypto_id, symbol in SUPPORTED_CRYPTOS.items():
        buttons.append(InlineKeyboardButton(
            text=f"{symbol}",
            callback_data=f"crypto:{crypto_id}"
        ))
    
    keyboard.add(*buttons)
    
    return keyboard

# Buy inline keyboard for specific cryptocurrency
def get_buy_inline_keyboard(crypto_id: str) -> InlineKeyboardMarkup:
    """Create buy inline keyboard for a specific cryptocurrency."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Predefined amounts to buy
    amounts = [10, 50, 100, 500, 1000]
    
    # Add buttons for each amount
    buttons = []
    for amount in amounts:
        buttons.append(InlineKeyboardButton(
            text=f"${amount}",
            callback_data=f"buy:{crypto_id}:{amount}"
        ))
    
    keyboard.add(*buttons)
    
    # Add custom amount button
    keyboard.add(InlineKeyboardButton(
        text="Custom Amount",
        callback_data=f"buy:{crypto_id}:custom"
    ))
    
    # Add back button
    keyboard.add(InlineKeyboardButton(
        text="🔙 Back",
        callback_data="back:cryptos"
    ))
    
    return keyboard

# Sell inline keyboard for a specific cryptocurrency
def get_sell_inline_keyboard(crypto_id: str, max_amount: float) -> InlineKeyboardMarkup:
    """Create sell inline keyboard for a specific cryptocurrency."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Sell 25%, 50%, 75%, 100% of holdings
    percentages = [25, 50, 75, 100]
    
    # Add buttons for each percentage
    buttons = []
    for percentage in percentages:
        buttons.append(InlineKeyboardButton(
            text=f"{percentage}%",
            callback_data=f"sell:{crypto_id}:{percentage}"
        ))
    
    keyboard.add(*buttons)
    
    # Add custom amount button
    keyboard.add(InlineKeyboardButton(
        text="Custom Amount",
        callback_data=f"sell:{crypto_id}:custom"
    ))
    
    # Add back button
    keyboard.add(InlineKeyboardButton(
        text="🔙 Back",
        callback_data="back:cryptos"
    ))
    
    return keyboard

# Portfolio inline keyboard
def get_portfolio_inline_keyboard(portfolio: Dict[str, Dict]) -> InlineKeyboardMarkup:
    """Create portfolio inline keyboard."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Add button for each cryptocurrency in portfolio
    for crypto_id, data in portfolio.items():
        if crypto_id in SUPPORTED_CRYPTOS and data.get('amount', 0) > 0:
            symbol = SUPPORTED_CRYPTOS[crypto_id]
            keyboard.add(InlineKeyboardButton(
                text=f"{symbol} - View Details",
                callback_data=f"portfolio:{crypto_id}"
            ))
    
    # If portfolio is empty, add a button to buy crypto
    if not portfolio or all(data.get('amount', 0) == 0 for data in portfolio.values()):
        keyboard.add(InlineKeyboardButton(
            text="Buy Cryptocurrency",
            callback_data="navigate:buy"
        ))
    
    return keyboard

# Admin statistics inline keyboard
def get_admin_stats_inline_keyboard() -> InlineKeyboardMarkup:
    """Create admin statistics inline keyboard."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    keyboard.add(InlineKeyboardButton(
        text="User Statistics",
        callback_data="admin:user_stats"
    ))
    keyboard.add(InlineKeyboardButton(
        text="Transaction Statistics",
        callback_data="admin:transaction_stats"
    ))
    keyboard.add(InlineKeyboardButton(
        text="Cryptocurrency Statistics",
        callback_data="admin:crypto_stats"
    ))
    
    return keyboard

# Admin user management inline keyboard
def get_admin_users_inline_keyboard(users: List[Dict]) -> InlineKeyboardMarkup:
    """Create admin user management inline keyboard."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Add buttons for each user (limit to 10 for UI reasons)
    for user in users[:10]:
        keyboard.add(InlineKeyboardButton(
            text=f"{user['username']} (ID: {user['telegram_id']})",
            callback_data=f"admin:user:{user['telegram_id']}"
        ))
    
    return keyboard

# Pagination inline keyboard
def get_pagination_inline_keyboard(
    current_page: int, 
    total_pages: int, 
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """Create pagination inline keyboard."""
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    buttons = []
    
    # Previous page button
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ Previous",
            callback_data=f"{callback_prefix}:{current_page - 1}"
        ))
    
    # Current page indicator
    buttons.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="pagination:noop"
    ))
    
    # Next page button
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            text="Next ▶️",
            callback_data=f"{callback_prefix}:{current_page + 1}"
        ))
    
    keyboard.add(*buttons)
    
    return keyboard
