
import logging
from database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_existing_users_balance():
    """Add 500 rubles to all existing users' balance"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Get all users
            cursor.execute("SELECT user_id, balance FROM users")
            users = cursor.fetchall()
            
            if not users:
                logger.info("No users found to update")
                return
            
            # Update each user's balance
            for user in users:
                current_balance = user['balance']
                new_balance = current_balance + 500
                
                cursor.execute(
                    "UPDATE users SET balance = ? WHERE user_id = ?",
                    (new_balance, user['user_id'])
                )
                
                logger.info(f"Updated user {user['user_id']} balance from {current_balance} to {new_balance}")
            
            conn.commit()
            logger.info(f"Successfully updated balance for {len(users)} users")
            
    except Exception as e:
        logger.error(f"Error updating user balances: {e}")
        logger.exception("Details:")

if __name__ == "__main__":
    update_existing_users_balance()
