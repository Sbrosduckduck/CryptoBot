import os

# Токен бота
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8148706555:AAGDZk0j17b8LS-Gsh3z9KG9y61Zboh06-4')

# Настройки администратора
ADMIN_EMAIL = 'sbrosduckduck@gmail.com'
ADMIN_IDS = [7328173250, 123456789]  # Добавили тестового пользователя

# Настройки базы данных
DATABASE_NAME = 'crypto_bot.db'

# Настройки логирования
LOG_FILE = 'bot.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'DEBUG'  # Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Минимальная сумма для пополнения/вывода
MIN_AMOUNT = 100
MAX_AMOUNT = 1000000

# Сообщения
MESSAGES = {
    'start': 'Добро пожаловать в CryptoBot! Для начала работы необходимо зарегистрироваться.',
    'help': 'Выберите действие с помощью кнопок ниже:',
    'admin_help': 'Админ-панель. Выберите действие:',
}

# Кнопки меню
USER_BUTTONS = [
    ['💼 Профиль', '💰 Баланс'],
    ['📥 Пополнить', '📤 Вывести'],
    ['📊 Мой портфель', '🏦 Криптовалюты']
]

ADMIN_BUTTONS = [
    ['📊 Статистика', '👥 Пользователи'],
    ['💰 Транзакции', '➕ Добавить крипту'],
    ['✏️ Редактировать крипту', '↩️ Обычное меню']
]