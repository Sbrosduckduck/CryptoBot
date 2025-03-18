from admin_handlers import ADMIN_EMAIL  # Remove ADMIN_BUTTONS import
import logging
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext, ConversationHandler, CallbackQueryHandler, 
    MessageHandler, Filters, CommandHandler
)
from database import (
    add_user, get_user, add_transaction, get_db, get_all_cryptos, 
    get_crypto_by_id, buy_crypto, sell_crypto, get_price_history
)
# Импортируем из модуля utils.py, а не из пакета utils
from utils import validate_email_address, validate_phone_number, validate_date, format_money, is_admin, format_crypto_amount
from typing import Dict

# Add this after the imports
USER_BUTTONS = [
    ["💼 Профиль", "💰 Баланс"],
    ["📥 Пополнить", "📤 Вывести"],
    ["📊 Мой портфель", "🏦 Криптовалюты"]
]

# Configuration
logger = logging.getLogger(__name__)

# State definitions for conversations
FIRST_NAME, LAST_NAME, MIDDLE_NAME, BIRTH_DATE, EMAIL, PHONE = range(6)

def get_keyboard(user=None):
    """Возвращает соответствующую клавиатуру в зависимости от прав пользователя"""
    if user and is_admin(user):
        from admin_handlers import ADMIN_BUTTONS  # Import ADMIN_BUTTONS only when needed
        return ReplyKeyboardMarkup(ADMIN_BUTTONS, resize_keyboard=True)
    return ReplyKeyboardMarkup(USER_BUTTONS, resize_keyboard=True)

def start(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if user:
        keyboard = get_keyboard(user)
        update.message.reply_text(
            f"Добро пожаловать обратно, {user['first_name']}!",
            reply_markup=keyboard
        )
    else:
        update.message.reply_text(
            "Добро пожаловать в CryptoBot! Используйте /register для регистрации."
        )

def register_start(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if user:
        update.message.reply_text(
            "Вы уже зарегистрированы!"
        )
        return ConversationHandler.END

    update.message.reply_text("Регистрация нового пользователя. Введите ваше имя:")
    return FIRST_NAME

def first_name(update: Update, context: CallbackContext):
    context.user_data['first_name'] = update.message.text
    update.message.reply_text("Введите вашу фамилию:")
    return LAST_NAME

def last_name(update: Update, context: CallbackContext):
    context.user_data['last_name'] = update.message.text
    update.message.reply_text("Введите ваше отчество:")
    return MIDDLE_NAME

def middle_name(update: Update, context: CallbackContext):
    context.user_data['middle_name'] = update.message.text
    update.message.reply_text(
        "Введите дату рождения в формате ДД.ММ.ГГГГ:"
    )
    return BIRTH_DATE

def birth_date(update: Update, context: CallbackContext):
    date = update.message.text
    if not validate_date(date):
        update.message.reply_text(
            "Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ):"
        )
        return BIRTH_DATE

    context.user_data['birth_date'] = date
    update.message.reply_text("Введите ваш email:")
    return EMAIL

def email(update: Update, context: CallbackContext):
    email = update.message.text
    if not validate_email_address(email):
        update.message.reply_text(
            "Неверный формат email. Попробуйте снова:"
        )
        return EMAIL

    context.user_data['email'] = email
    update.message.reply_text(
        "Введите номер телефона в формате +7XXXXXXXXXX:"
    )
    return PHONE

def phone(update: Update, context: CallbackContext):
    phone = update.message.text
    if not validate_phone_number(phone):
        update.message.reply_text(
            "Неверный формат телефона. Попробуйте снова (+7XXXXXXXXXX):"
        )
        return PHONE

    context.user_data['phone'] = phone

    # Сохраняем пользователя и добавляем бонус 250 рублей
    user_data = {
        'user_id': update.effective_user.id,
        'balance': 250,  # Добавляем бонус при регистрации
        **context.user_data
    }
    add_user(user_data)

    update.message.reply_text(
        "Регистрация успешно завершена!\n"
        "Вам начислен бонус 250₽ за регистрацию.\n"
        "Теперь вы можете пользоваться всеми функциями бота."
    )
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Регистрация отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def profile(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if not user:
        update.message.reply_text(
            "Вы не зарегистрированы. Используйте /register для регистрации."
        )
        return

    profile_text = f"""
👤 Профиль пользователя:
Имя: {user['first_name']}
Фамилия: {user['last_name']}
Отчество: {user['middle_name']}
Email: {user['email']}
Телефон: {user['phone']}
Баланс: {format_money(user['balance'])}
    """
    update.message.reply_text(profile_text)

def deposit(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if not user:
        update.message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    args = context.args
    if not args or not args[0].isdigit():
        update.message.reply_text(
            "Использование: /deposit <сумма>"
        )
        return

    amount = float(args[0])
    if amount < 100:
        update.message.reply_text("Минимальная сумма пополнения: 100 ₽")
        return

    # Создаем заявку на пополнение
    transaction_id = add_transaction(user['user_id'], 'deposit', amount)
    
    # Получаем уникальный ID транзакции
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT unique_id FROM transactions WHERE id = ?", (transaction_id,))
        unique_id = cursor.fetchone()['unique_id']
        last_six = str(unique_id)[-6:] if unique_id else 'XXXXXX'

    update.message.reply_text(
        f"🏦 Заявка на пополнение создана\n\n"
        f"Сумма: {format_money(amount)}\n"
        f"ID транзакции: #{unique_id}\n\n"
        "💳 Для пополнения переведите указанную сумму на карту:\n"
        "2204 3204 1877 7332\n\n"
        f"❗️ Важно: укажите {last_six} в комментарии к переводу\n\n"
        "После выполнения перевода ожидайте подтверждения от администратора."
    )

def withdraw(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if not user:
        update.message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    args = context.args
    if not args or not args[0].isdigit():
        update.message.reply_text(
            "Использование: /withdraw <сумма>"
        )
        return

    amount = float(args[0])
    if amount < 100:
        update.message.reply_text("Минимальная сумма вывода: 100 ₽")
        return

    if amount > user['balance']:
        update.message.reply_text("Недостаточно средств на балансе!")
        return

    # Создаем заявку на вывод
    add_transaction(user['user_id'], 'withdraw', amount)

    update.message.reply_text(
        f"Создана заявка на вывод на сумму {format_money(amount)}.\n"
        "Ожидайте подтверждения от администратора."
    )

def handle_button(update: Update, context: CallbackContext):
    """Обрабатывает нажатия на кнопки клавиатуры"""
    logger.info("Обработка нажатия кнопки")

    text = update.message.text
    user = get_user(update.effective_user.id)

    if not user:
        logger.warning(f"Неавторизованный доступ от пользователя {update.effective_user.id}")
        update.message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    logger.info(f"Пользователь {user['user_id']} нажал кнопку: {text}")

    # Кнопки администратора
    if is_admin(user):
        if text == "📊 Статистика":
            from admin_handlers import admin_stats
            admin_stats(update, context)
            return
        elif text == "👥 Пользователи":
            from admin_handlers import show_users
            show_users(update, context)
            return
        elif text == "💰 Транзакции":  # Добавляем обработку кнопки транзакций
            from admin_handlers import view_transactions
            view_transactions(update, context)
            return
        elif text == "📥 Заявки":  # Добавляем обработку кнопки заявок на пополнение/вывод
            from admin_handlers import view_pending_transactions
            view_pending_transactions(update, context)
            return
        elif text == "➕ Добавить крипту":
            from admin_handlers import add_crypto_command
            add_crypto_command(update, context)
            return
        elif text == "✏️ Редактировать крипту":
            from admin_handlers import edit_crypto_command
            edit_crypto_command(update, context)
            return
        elif text == "↩️ Обычное меню":
            keyboard = get_keyboard()
            update.message.reply_text("Обычный режим.", reply_markup=keyboard)
            return

    # Кнопки пользователя
    if text == "💼 Профиль":
        profile(update, context)
    elif text == "💰 Баланс":
        show_balance(update, context)
    elif text == "📥 Пополнить":
        show_deposit_info(update, context)
    elif text == "📤 Вывести":
        show_withdraw_info(update, context)
    elif text == "📊 Мой портфель":
        show_portfolio(update, context)
    elif text == "🏦 Криптовалюты":
        show_available_cryptos(update, context)



def show_balance(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    update.message.reply_text(f"Ваш баланс: {format_money(user['balance'])}")

def show_deposit_info(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Для пополнения баланса используйте команду:\n"
        "/deposit <сумма>\n"
        f"Минимальная сумма: {format_money(100)}"
    )

def show_withdraw_info(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Для вывода средств используйте команду:\n"
        "/withdraw <сумма>\n"
        f"Минимальная сумма: {format_money(100)}"
    )

def buy_crypto_handler(update: Update, context: CallbackContext):
    """Обрабатывает нажатие на кнопку покупки криптовалюты"""
    logger.info("Вызвана функция buy_crypto_handler")
    query = update.callback_query
    query.answer()

    user = get_user(query.from_user.id)
    if not user:
        logger.warning(f"Неавторизованный доступ от пользователя {query.from_user.id}")
        query.message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    # Получаем ID криптовалюты из callback_data
    crypto_id = int(query.data.split('_')[1])
    logger.info(f"Пользователь {user['user_id']} выбрал криптовалюту ID: {crypto_id}")

    # Получаем информацию о криптовалюте
    crypto = get_crypto_by_id(crypto_id)
    if not crypto:
        query.message.reply_text("Криптовалюта не найдена.")
        return

    # Запоминаем данные для покупки
    context.user_data['buying_crypto_id'] = crypto_id
    context.user_data['buying_crypto_name'] = crypto['name']
    context.user_data['buying_crypto_symbol'] = crypto['symbol']
    context.user_data['buying_crypto_rate'] = crypto['rate']

    message = f"🛒 Покупка криптовалюты\n\n"
    message += f"Вы выбрали {crypto['name']} ({crypto['symbol']})\n"
    message += f"Курс: {format_money(crypto['rate'])}₽\n"
    message += f"Ваш баланс: {format_money(user['balance'])}₽\n\n"

    # Вычисляем максимальное количество, которое может купить пользователь
    max_affordable = user['balance'] / crypto['rate']
    max_available = crypto['available_supply']
    max_possible = min(max_affordable, max_available)

    context.user_data['max_crypto_amount'] = max_possible

    message += f"Максимально доступно для покупки: {format_crypto_amount(max_possible)} {crypto['symbol']}\n\n"
    message += "💭 Введите количество для покупки или нажмите на одну из кнопок ниже:"

    # Создаем кнопки для выбора суммы
    keyboard = []

    # Кнопки для процентов от максимума
    percentages = [10, 25, 50, 75, 100]
    keyboard_row = []

    for percent in percentages:
        amount = max_possible * (percent / 100)
        if amount > 0:
            keyboard_row.append(InlineKeyboardButton(
                f"{percent}% ({format_crypto_amount(amount)})",
                callback_data=f"buyamt_{crypto_id}_{amount:.8f}"
            ))

        # Добавляем по 3 кнопки в строку
        if len(keyboard_row) == 3 or percent == percentages[-1]:
            keyboard.append(keyboard_row)
            keyboard_row = []

    # Кнопка отмены
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="buycancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(message, reply_markup=reply_markup)
    logger.info(f"Показано меню покупки для пользователя {user['user_id']}")

    # Регистрируем обработчик колбэка для суммы
    context.dispatcher.add_handler(
        CallbackQueryHandler(
            process_crypto_purchase_callback,
            pattern=r'^buyamt_|^buycancel$'
        ),
        group=1
    )

    # Регистрируем обработчик следующего сообщения
    context.dispatcher.add_handler(
        MessageHandler(
            Filters.text & ~Filters.command,
            process_crypto_purchase,
            pass_user_data=True
        ),
        group=2  # Используем отдельную группу, чтобы не конфликтовать с другими обработчиками
    )

def process_crypto_purchase(update: Update, context: CallbackContext):
    """Обрабатывает ввод количества криптовалюты для покупки"""
    # Удаляем временные обработчики
    for handler in context.dispatcher.handlers.get(1, []):
        context.dispatcher.remove_handler(handler, 1)
    for handler in context.dispatcher.handlers.get(2, []):
        context.dispatcher.remove_handler(handler, 2)

    user = get_user(update.effective_user.id)
    if not user:
        update.message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    # Проверяем, что у нас есть необходимые данные
    if 'buying_crypto_id' not in context.user_data:
        update.message.reply_text("Ошибка: сессия покупки истекла. Пожалуйста, начните заново.")
        return

    try:
        # Парсим ввод пользователя
        amount = float(update.message.text.strip().replace(',', '.'))
        if amount <= 0:
            update.message.reply_text("Количество должно быть положительным числом.")
            return
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректное число.")
        return

    crypto_id = context.user_data['buying_crypto_id']
    crypto_name = context.user_data['buying_crypto_name']
    crypto_symbol = context.user_data['buying_crypto_symbol']
    crypto_rate = context.user_data['buying_crypto_rate']
    max_amount = context.user_data.get('max_crypto_amount', 0)

    # Проверяем, не превышает ли выбранное количество максимально доступное
    if amount > max_amount:
        update.message.reply_text(
            f"Ошибка: выбранное количество ({format_crypto_amount(amount)}) "
            f"превышает максимально доступное ({format_crypto_amount(max_amount)})."
        )
        return

    # Проверяем, достаточно ли у пользователя средств
    total_cost = amount * crypto_rate
    if total_cost > user['balance']:
        update.message.reply_text(
            f"Недостаточно средств. Необходимо: {format_money(total_cost)}₽, "
            f"у вас: {format_money(user['balance'])}₽"
        )
        return

    # Попытка совершить покупку
    if buy_crypto(user['user_id'], crypto_id, amount):
        update.message.reply_text(
            f"✅ Успешная покупка!\n\n"
            f"Вы приобрели {format_crypto_amount(amount)} {crypto_symbol} "
            f"на сумму {format_money(total_cost)}₽\n\n"
            f"Ваш баланс: {format_money(user['balance'] - total_cost)}₽"
        )
    else:
        update.message.reply_text(
            "❌ Ошибка при совершении покупки. Возможно, недостаточно доступной криптовалюты."
        )

    # Очищаем данные покупки
    for key in list(context.user_data.keys()):
        if key.startswith('buying_crypto_') or key == 'max_crypto_amount':
            del context.user_data[key]

def process_crypto_purchase_callback(update: Update, context: CallbackContext):
    """Обрабатывает колбэки кнопок при покупке криптовалюты"""
    query = update.callback_query
    query.answer()

    try:
        logger.info(f"Колбэк покупки криптовалюты: {query.data}")

        # Проверяем на отмену
        if query.data == "buycancel":
            query.message.reply_text("🚫 Покупка отменена.")
            # Очищаем данные покупки
            for key in list(context.user_data.keys()):
                if key.startswith('buying_crypto_') or key == 'max_crypto_amount':
                    del context.user_data[key]
            return

        # Проверка на колбэк продажи
        if query.data.startswith("sell_"):
            sell_crypto_handler(update, context)
            return

        # Обработка подтверждения покупки
        elif query.data.startswith("buyconfirm_"):
            # Данный блок будет обработан специальной веткой ниже
            pass

        user = get_user(query.from_user.id)
        if not user:
            logger.warning(f"Неавторизованный доступ от пользователя {query.from_user.id}")
            query.message.reply_text("Сначала необходимо зарегистрироваться!")
            return

        # Обработка просмотра портфеля после покупки/продажи
        if query.data == "show_portfolio":
            show_portfolio(update, context)
            return

        # Обработка выбора криптовалюты
        if query.data.startswith("buy_"):
            if query.data == "buy_more_crypto":
                show_available_cryptos(update, context)
                return

            crypto_id = int(query.data.split('_')[1])
            logger.info(f"Пользователь {user['user_id']} выбрал криптовалюту ID: {crypto_id}")

            # Получаем информацию о криптовалюте
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, symbol, rate, available_supply FROM cryptocurrencies WHERE id = ?", (crypto_id,))
                crypto = cursor.fetchone()
                if not crypto:
                    query.message.reply_text("Криптовалюта не найдена.")
                    return

            # Запоминаем данные для покупки
            context.user_data['buying_crypto_id'] = crypto_id
            context.user_data['buying_crypto_name'] = crypto['name']
            context.user_data['buying_crypto_symbol'] = crypto['symbol']
            context.user_data['buying_crypto_rate'] = crypto['rate']

            message = f"🛒 Покупка криптовалюты\n\n"
            message += f"Вы выбрали {crypto['name']} ({crypto['symbol']})\n"
            message += f"Курс: {format_money(crypto['rate'])}₽\n"
            message += f"Ваш баланс: {format_money(user['balance'])}₽\n\n"

            # Вычисляем максимальное количество, которое может купить пользователь
            max_affordable = user['balance'] / crypto['rate']
            max_available = crypto['available_supply']
            max_possible = min(max_affordable, max_available)

            context.user_data['max_crypto_amount'] = max_possible

            message += f"Максимально доступно для покупки: {format_crypto_amount(max_possible)} {crypto['symbol']}\n\n"
            message += "💭 Введите количество для покупки или нажмите на одну из кнопок ниже:"

            # Создаем кнопки для выбора суммы
            keyboard = []

            # Кнопки для процентов от максимума
            percentages = [10, 25, 50, 75, 100]
            keyboard_row = []

            for percent in percentages:
                amount = max_possible * (percent / 100)
                if amount > 0:
                    keyboard_row.append(InlineKeyboardButton(
                        f"{percent}% ({format_crypto_amount(amount)})",
                        callback_data=f"buyamt_{crypto_id}_{amount:.8f}"
                    ))

                # Добавляем по 3 кнопки в строку
                if len(keyboard_row) == 3 or percent == percentages[-1]:
                    keyboard.append(keyboard_row)
                    keyboard_row = []

            # Кнопка отмены
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="buycancel")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(message, reply_markup=reply_markup)
            logger.info(f"Показано меню покупки для пользователя {user['user_id']}")
            return

        # Обработка выбора суммы покупки
        elif query.data.startswith("buyamt_"):
            # Получаем данные о покупке
            _, crypto_id, amount_str = query.data.split('_')
            crypto_id = int(crypto_id)
            amount = float(amount_str)

            # Проверяем, что у нас есть необходимые данные в контексте
            if 'buying_crypto_id' not in context.user_data or context.user_data['buying_crypto_id'] != crypto_id:
                query.message.reply_text("Ошибка: сессия покупки истекла. Пожалуйста, начните заново.")
                return

            crypto_name = context.user_data['buying_crypto_name']
            crypto_symbol = context.user_data['buying_crypto_symbol']
            crypto_rate = context.user_data['buying_crypto_rate']
            max_amount = context.user_data.get('max_crypto_amount', 0)

            # Проверяем, не превышает ли выбранное количество максимально доступное
            if amount > max_amount:
                query.message.reply_text(
                    f"Ошибка: выбранное количество ({format_crypto_amount(amount)}) "
                    f"превышает максимально доступное ({format_crypto_amount(max_amount)})."
                )
                return

            # Проверяем, достаточно ли у пользователя средств
            total_cost = amount * crypto_rate
            if total_cost > user['balance']:
                query.message.reply_text(
                    f"Недостаточно средств. Необходимо: {format_money(total_cost)}₽, "
                    f"у вас: {format_money(user['balance'])}₽"
                )
                return

            # Запрашиваем подтверждение с показом деталей покупки
            message = f"⚠️ Подтверждение покупки\n\n"
            message += f"Криптовалюта: {crypto_name} ({crypto_symbol})\n"
            message += f"Количество: {format_crypto_amount(amount)} {crypto_symbol}\n"
            message += f"Цена за единицу: {format_money(crypto_rate)}₽\n"
            message += f"Итоговая стоимость: {format_money(total_cost)}₽\n\n"
            message += "Подтвердите покупку или отмените:"

            keyboard = [
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"buyconfirm_{crypto_id}_{amount:.8f}"),
                    InlineKeyboardButton("❌ Отмена", callback_data="buycancel")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(message, reply_markup=reply_markup)
            return

        # Обработка подтверждения покупки
        elif query.data.startswith("buyconfirm_"):
            # Получаем данные о покупке
            _, crypto_id, amount_str = query.data.split('_')
            crypto_id = int(crypto_id)
            amount = float(amount_str)

            # Получаем пользователя
            user = get_user(query.from_user.id)
            if not user:
                query.message.reply_text("Ошибка: пользователь не найден. Пожалуйста, зарегистрируйтесь.")
                return

            # Проверяем, что у нас есть необходимые данные в контексте
            if 'buying_crypto_id' not in context.user_data:
                # Получаем информацию о криптовалюте напрямую из БД, если нет в контексте
                crypto = get_crypto_by_id(crypto_id)
                if not crypto:
                    query.message.reply_text("Ошибка: криптовалюта не найдена. Пожалуйста, начните заново.")
                    return

                crypto_symbol = crypto['symbol']
                crypto_rate = crypto['rate']
            else:
                crypto_symbol = context.user_data.get('buying_crypto_symbol', 'Unknown')
                crypto_rate = context.user_data.get('buying_crypto_rate', 0)

            # Вычисляем стоимость
            total_cost = amount * crypto_rate

            # Проверяем, достаточно ли у пользователя средств
            if total_cost > user['balance']:
                query.message.reply_text(
                    f"Недостаточно средств. Необходимо: {format_money(total_cost)}₽, "
                    f"у вас: {format_money(user['balance'])}₽"
                )
                return

            # Попытка совершить покупку
            logger.info(f"Пользователь {user['user_id']} пытается купить {amount} {crypto_symbol} за {total_cost}₽")
            if buy_crypto(user['user_id'], crypto_id, amount):
                # Получаем обновленный баланс пользователя
                updated_user = get_user(user['user_id'])
                logger.info(f"Покупка успешно совершена. Новый баланс: {updated_user['balance']}₽")

                query.message.reply_text(
                    f"✅ Успешная покупка!\n\n"
                    f"Вы приобрели {format_crypto_amount(amount)} {crypto_symbol} "
                    f"на сумму {format_money(total_cost)}₽\n\n"
                    f"Ваш текущий баланс: {format_money(updated_user['balance'])}₽"
                )

                # Отправляем сообщение с предложением посмотреть портфель
                keyboard = [
                    [InlineKeyboardButton("📊 Мой портфель", callback_data="show_portfolio")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    "Хотите посмотреть ваш обновленный портфель?",
                    reply_markup=reply_markup
                )
            else:
                logger.error(f"Ошибка при покупке криптовалюты: user_id={user['user_id']}, crypto_id={crypto_id}, amount={amount}")
                query.message.reply_text(
                    "❌ Ошибка при совершении покупки. Возможно, недостаточно доступной криптовалюты."
                )

            # Очищаем данные покупки
            for key in list(context.user_data.keys()):
                if key.startswith('buying_crypto_') or key == 'max_crypto_amount':
                    del context.user_data[key]

        # Обработка просмотра портфеля
        elif query.data == "show_portfolio":
            show_portfolio(update, context)

    except Exception as e:
        logger.error(f"Ошибка при обработке колбэка покупки: {str(e)}")
        logger.exception("Полные детали ошибки:")
        query.message.reply_text(
            "Произошла ошибка при обработке запроса. "
            "Пожалуйста, попробуйте заново."
        )

def sell_crypto_handler(update: Update, context: CallbackContext):
    """Обрабатывает нажатие на кнопку продажи криптовалюты"""
    logger.info("Called sell_crypto_handler")
    query = update.callback_query
    query.answer()

    user = get_user(query.from_user.id)
    if not user:
        logger.warning(f"Unauthorized access attempt from user {query.from_user.id}")
        query.message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    try:
        # Получаем ID криптовалюты из callback_data
        crypto_id = int(query.data.split('_')[1])
        logger.info(f"User {user['user_id']} selected crypto ID: {crypto_id} for selling")

        # Получаем информацию о криптовалюте
        crypto = get_crypto_by_id(crypto_id)
        if not crypto:
            logger.error(f"Cryptocurrency with ID {crypto_id} not found")
            query.message.reply_text("Криптовалюта не найдена.")
            return

        # Получаем портфель пользователя для этой криптовалюты
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT amount FROM portfolios 
                WHERE user_id = ? AND crypto_id = ?
            """, (user['user_id'], crypto_id))
            portfolio = cursor.fetchone()

        if not portfolio or portfolio['amount'] <= 0:
            logger.warning(f"User {user['user_id']} attempted to sell crypto {crypto_id} but has no balance")
            query.message.reply_text(
                f"У вас нет {crypto['symbol']} для продажи."
            )
            return

        # Сохраняем данные для продажи в контексте
        context.user_data['selling_crypto_id'] = crypto_id
        context.user_data['selling_crypto_name'] = crypto['name']
        context.user_data['selling_crypto_symbol'] = crypto['symbol']
        context.user_data['selling_crypto_rate'] = crypto['rate']
        context.user_data['max_sell_amount'] = portfolio['amount']

        logger.info(f"User {user['user_id']} can sell up to {portfolio['amount']} {crypto['symbol']}")

        # Формируем сообщение
        message = f"💰 Продажа криптовалюты\n\n"
        message += f"Вы выбрали {crypto['name']} ({crypto['symbol']})\n"
        message += f"Текущий курс: {format_money(crypto['rate'])}₽\n"
        message += f"У вас в наличии: {format_crypto_amount(portfolio['amount'])} {crypto['symbol']}\n\n"
        message += "💭 Введите количество для продажи или нажмите на одну из кнопок ниже:"

        # Создаем кнопки для выбора суммы
        keyboard = []
        percentages = [10, 25, 50, 75, 100]
        keyboard_row = []

        for percent in percentages:
            amount = portfolio['amount'] * (percent / 100)
            if amount > 0:
                keyboard_row.append(InlineKeyboardButton(
                    f"{percent}% ({format_crypto_amount(amount)})",
                    callback_data=f"sellamt_{crypto_id}_{amount:.8f}"
                ))

            if len(keyboard_row) == 3 or percent == percentages[-1]:
                keyboard.append(keyboard_row)
                keyboard_row = []

        # Кнопка отмены
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="sellcancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(message, reply_markup=reply_markup)
        logger.info(f"Sell menu shown to user {user['user_id']}")

    except Exception as e:
        logger.error(f"Error in sell_crypto_handler: {str(e)}")
        logger.exception("Full error details:")
        query.message.reply_text(
            "Произошла ошибка при обработке запроса. "
            "Пожалуйста, попробуйте позже."
        )

def process_crypto_sell_callback(update: Update, context: CallbackContext):
    """Обрабатывает колбэки кнопок при продаже криптовалюты"""
    query = update.callback_query
    logger.info(f"Received callback query: {query.data}")

    try:
        if not query.data:
            logger.error("Empty callback data received")
            return

        logger.info(f"Processing sell callback with data: {query.data}")
        query.answer()

        # First check for cancellation
        if query.data == "sellcancel":
            logger.info("User cancelled the sell operation")
            query.message.reply_text("🚫 Продажа отменена.")
            context.user_data.clear()
            return

        # Handle portfolio view request
        if query.data == "show_portfolio":
            logger.info("User requested to view portfolio")
            show_portfolio(update, context)
            return

        # Get user information
        user = get_user(query.from_user.id)
        if not user:
            logger.warning(f"Unauthorized access attempt from user {query.from_user.id}")
            query.message.reply_text("Сначала необходимо зарегистрироваться!")
            return

        # Process sell amount selection
        if query.data.startswith("sell_"):
            crypto_id = int(query.data.split('_')[1])
            logger.info(f"User {user['user_id']} initiating sale of crypto {crypto_id}")

            # Get crypto details
            crypto = get_crypto_by_id(crypto_id)
            if not crypto:
                logger.error(f"Cryptocurrency {crypto_id} not found")
                query.message.reply_text("Криптовалюта не найдена.")
                return

            # Get user's portfolio
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT amount FROM portfolios 
                    WHERE user_id = ? AND crypto_id = ?
                """, (user['user_id'], crypto_id))
                portfolio = cursor.fetchone()

            if not portfolio or portfolio['amount'] <= 0:
                logger.warning(f"User {user['user_id']} has no {crypto['symbol']} to sell")
                query.message.reply_text(
                    f"У вас нет {crypto['symbol']} для продажи."
                )
                return

            # Store sale context
            context.user_data.update({
                'selling_crypto_id': crypto_id,
                'selling_crypto_name': crypto['name'],
                'selling_crypto_symbol': crypto['symbol'],
                'selling_crypto_rate': crypto['rate'],
                'max_sell_amount': portfolio['amount']
            })

            # Show sell menu
            show_sell_menu(update, context, crypto, portfolio['amount'])
            return

        # Handle amount selection
        if query.data.startswith("sellamt_"):
            handle_sell_amount_selection(update, context)
            return

        # Handle sale confirmation
        if query.data.startswith("sellconfirm_"):
            handle_sell_confirmation(update, context)
            return

    except Exception as e:
        logger.error(f"Error in process_crypto_sell_callback: {str(e)}")
        logger.exception("Full error details:")
        query.message.reply_text(
            "Произошла ошибка при обработке запроса. "
            "Пожалуйста, попробуйте позже."
        )
        context.user_data.clear()

def show_sell_menu(update: Update, context: CallbackContext, crypto: Dict, available_amount: float):
    """Показывает меню продажи криптовалюты"""
    query = update.callback_query

    message = f"💰 Продажа криптовалюты\n\n"
    message += f"Вы выбрали {crypto['name']} ({crypto['symbol']})\n"
    message += f"Текущий курс: {format_money(crypto['rate'])}₽\n"
    message += f"У вас в наличии: {format_crypto_amount(available_amount)} {crypto['symbol']}\n\n"
    message += "💭 Выберите количество для продажи:"

    # Create buttons for percentage selection
    keyboard = []
    percentages = [10, 25, 50, 75, 100]
    keyboard_row = []

    for percent in percentages:
        amount = available_amount * (percent / 100)
        if amount > 0:
            keyboard_row.append(InlineKeyboardButton(
                f"{percent}% ({format_crypto_amount(amount)})",
                callback_data=f"sellamt_{crypto['id']}_{amount:.8f}"
            ))

        if len(keyboard_row) == 3 or percent == percentages[-1]:
            keyboard.append(keyboard_row)
            keyboard_row = []

    # Add cancel button
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="sellcancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(message, reply_markup=reply_markup)
    logger.info(f"Sell menu shown for crypto {crypto['id']}")

def handle_sell_amount_selection(update: Update, context: CallbackContext):
    """Обрабатывает выбор количества криптовалюты для продажи"""
    query = update.callback_query

    try:
        _, crypto_id, amount_str = query.data.split('_')
        crypto_id = int(crypto_id)
        amount = float(amount_str)

        if 'selling_crypto_id' not in context.user_data:
            logger.error(f"Missing selling context for user {query.from_user.id}")
            query.message.reply_text("Ошибка: сессия продажи истекла. Пожалуйста, начните заново.")
            return

        if amount > context.user_data['max_sell_amount']:
            logger.warning(f"Attempted to sell more than available: {amount} > {context.user_data['max_sell_amount']}")
            query.message.reply_text(
                f"Недостаточно криптовалюты. Максимально доступно: "
                f"{format_crypto_amount(context.user_data['max_sell_amount'])} "
                f"{context.user_data['selling_crypto_symbol']}"
            )
            return

        # Calculate sale value
        sale_value = amount * context.user_data['selling_crypto_rate']

        # Show confirmation message
        message = f"⚠️ Подтверждение продажи\n\n"
        message += f"Криптовалюта: {context.user_data['selling_crypto_name']} ({context.user_data['selling_crypto_symbol']})\n"
        message += f"Количество: {format_crypto_amount(amount)} {context.user_data['selling_crypto_symbol']}\n"
        message += f"Курс: {format_money(context.user_data['selling_crypto_rate'])}₽\n"
        message += f"Вы получите: {format_money(sale_value)}₽\n\n"
        message += "Подтвердите продажу:"

        keyboard = [[
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"sellconfirm_{crypto_id}_{amount:.8f}"),
            InlineKeyboardButton("❌ Отмена", callback_data="sellcancel")
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(message, reply_markup=reply_markup)
        logger.info(f"Sale confirmation requested for {amount} of crypto {crypto_id}")

    except Exception as e:
        logger.error(f"Error in handle_sell_amount_selection: {str(e)}")
        logger.exception("Full error details:")
        query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
        context.user_data.clear()

def handle_sell_confirmation(update: Update, context: CallbackContext):
    """Обрабатывает подтверждение продажи криптовалюты"""
    query = update.callback_query

    try:
        _, crypto_id, amount_str = query.data.split('_')
        crypto_id = int(crypto_id)
        amount = float(amount_str)

        user = get_user(query.from_user.id)
        if not user:
            logger.error(f"User not found: {query.from_user.id}")
            query.message.reply_text("Ошибка: пользователь не найден.")
            return

        logger.info(f"Processing sale confirmation: {amount} of crypto {crypto_id} for user {user['user_id']}")

        if sell_crypto(user['user_id'], crypto_id, amount):
            # Get updated user balance
            updated_user = get_user(user['user_id'])
            sale_value = amount * context.user_data['selling_crypto_rate']

            query.message.reply_text(
                f"✅ Успешная продажа!\n\n"
                f"Продано: {format_crypto_amount(amount)} {context.user_data['selling_crypto_symbol']}\n"
                f"Получено: {format_money(sale_value)}₽\n\n"
                f"Ваш текущий баланс: {format_money(updated_user['balance'])}₽"
            )

            # Offer to view updated portfolio
            keyboard = [[InlineKeyboardButton("📊 Мой портфель", callback_data="show_portfolio")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(
                "Хотите посмотреть обновленный портфель?",
                reply_markup=reply_markup
            )
        else:
            logger.error(f"Failed to sell crypto {crypto_id} for user {user['user_id']}")
            query.message.reply_text(
                "❌ Ошибка при продаже криптовалюты. "
                "Пожалуйста, попробуйте позже."
            )

    except Exception as e:
        logger.error(f"Error in handle_sell_confirmation: {str(e)}")
        logger.exception("Full error details:")
        query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
    finally:
        context.user_data.clear()

def show_portfolio(update: Update, context: CallbackContext):
    """Показывает портфель пользователя"""
    logger.info("Called show_portfolio")

    # Определяем, откуда пришел запрос
    if update.callback_query:
        message = update.callback_query.message
        update.callback_query.answer()
    else:
        message = update.message

    user = get_user(message.chat.id)
    if not user:
        logger.warning(f"Unauthorized access attempt from user {message.chat.id}")
        message.reply_text("Сначала необходимо зарегистрироваться!")
        return

    try:
        # Получаем портфель пользователя
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, c.name, c.symbol, c.rate
                FROM portfolios p
                JOIN cryptocurrencies c ON p.crypto_id = c.id
                WHERE p.user_id = ? AND p.amount > 0
            """, (user['user_id'],))
            portfolio = cursor.fetchall()

        if not portfolio:
            logger.info(f"Empty portfolio for user {user['user_id']}")
            message.reply_text("Ваш портфель пуст. Используйте кнопку 🏦 Криптовалюты для покупки.")
            return

        # Формируем сообщение о портфеле
        text = "📊 Ваш криптопортфель:\n\n"
        total_value = 0
        keyboard = []

        for item in portfolio:
            value = item['amount'] * item['rate']
            total_value += value

            # Добавляем информацию о криптовалюте
            text += (
                f"• {item['name']} ({item['symbol']})\n"
                f"  Количество: {format_crypto_amount(item['amount'])} {item['symbol']}\n"
                f"  Курс: {format_money(item['rate'])}₽\n"
                f"  Стоимость: {format_money(value)}₽\n\n"
            )

            # Создаем кнопки для каждой криптовалюты
            row = [
                InlineKeyboardButton(
                    f"📈 График {item['symbol']}", 
                    callback_data=f"chart_{item['crypto_id']}"
                ),
                InlineKeyboardButton(
                    f"💰 Продать {item['symbol']}", 
                    callback_data=f"sell_{item['crypto_id']}"
                )
            ]
            keyboard.append(row)

        text += f"Общая стоимость портфеля: {format_money(total_value)}₽"

        # Добавляем кнопку для покупки новой криптовалюты
        keyboard.append([
            InlineKeyboardButton(
                "🛒 Купить криптовалюту", 
                callback_data="buy_more_crypto"
            )
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        message.reply_text(text, reply_markup=reply_markup)
        logger.info(f"Portfolio shown to user {user['user_id']}, total value: {total_value}")

    except Exception as e:
        logger.error(f"Error showing portfolio: {str(e)}")
        logger.exception("Full error details:")
        message.reply_text(
            "Произошла ошибка при получении данных портфеля. "
            "Пожалуйста, попробуйте позже."
        )

def show_graph(update: Update, context: CallbackContext):
    """Показывает график изменения цены криптовалюты"""
    query = update.callback_query
    query.answer()

    try:
        # Получаем ID криптовалюты из callback_data
        crypto_id = int(query.data.split('_')[1])
        logger.info(f"Показ графика для криптовалюты ID: {crypto_id}")

        # Получаем информацию о криптовалюте
        crypto = get_crypto_by_id(crypto_id)
        if not crypto:
            logger.warning(f"Криптовалюта {crypto_id} не найдена")
            query.message.reply_text("Криптовалюта не найдена.")
            return

        logger.info(f"Генерация графика для {crypto['name']} ({crypto['symbol']})")
        # Генерируем график
        chart_base64 = generate_price_graph(crypto_id, crypto['name'], crypto['symbol'])

        if not chart_base64:
            logger.warning(f"Не удалось сгенерировать график для {crypto['symbol']}")
            query.message.reply_text("Не удалось сгенерировать график. Возможно, недостаточно данных.")
            return

        # Получаем историю цен для вычисления изменений
        price_history = get_price_history(crypto_id, days=30)

        if price_history:
            first_price = price_history[0]['rate']
            last_price = price_history[-1]['rate']
            logger.info(f"Цена {crypto['symbol']}: начальная={first_price}, текущая={last_price}")

            # Вычисляем изменение в процентах
            price_change_pct = ((last_price - first_price) / first_price) * 100
            logger.info(f"Изменение цены {crypto['symbol']}: {price_change_pct:+.2f}%")

            # Определяем эмодзи в зависимости от изменения цены
            if price_change_pct > 0:
                emoji = "🟢"
            elif price_change_pct < 0:
                emoji = "🔴"
            else:
                emoji = "⚪"

            # Формируем подпись к графику
            caption = (
                f"📊 {crypto['name']} ({crypto['symbol']})\n\n"
                f"{emoji} Изменение: {price_change_pct:+.2f}%\n"
                f"Начальная цена: {format_money(first_price)}\n"
                f"Текущая цена: {format_money(last_price)}\n\n"
                f"Данные за последние 30 дней"
            )
        else:
            caption = f"📊 График {crypto['name']} ({crypto['symbol']})"
            logger.warning(f"Нет данных для расчета изменения цены {crypto['symbol']}")

        # Отправляем изображение
        import io
        import base64
        image_data = base64.b64decode(chart_base64)
        logger.info(f"Отправка графика пользователю для {crypto['symbol']}")
        query.message.reply_photo(
            photo=io.BytesIO(image_data),
            caption=caption
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении графика: {str(e)}")
        logger.exception("Полная информация об ошибке:")
        query.message.reply_text("Произошла ошибка при отображении графика.")

def generate_price_graph(crypto_id: int, crypto_name: str, crypto_symbol: str) -> str:
    """
    Генерирует график изменения цены криптовалюты и возвращает его в формате base64
    :return: base64 строка с графиком
    """
    try:
        logger.info(f"Начало генерации графика для {crypto_symbol}")
        # Получаем историю цен за последние 30 дней
        price_history = get_price_history(crypto_id, days=30)

        if not price_history:
            logger.warning(f"No price history found for crypto {crypto_id}")
            return None

        # Подготавливаем данные для графика
        dates = []
        prices = []
        for record in price_history:
            try:
                # SQLite возвращает строку в формате ISO
                date = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                price = float(record['rate'])
                dates.append(date)
                prices.append(price)
                logger.debug(f"Processed data point: date={date}, price={price}")
            except (ValueError, KeyError) as e:
                logger.error(f"Error parsing record {record}: {e}")
                continue

        if not dates or not prices:
            logger.error("No valid data points for graph")
            return None

        logger.info(f"Построение графика из {len(dates)} точек данных")

        # Создаем график
        plt.figure(figsize=(10, 6))
        plt.plot(dates, prices, marker='o', linestyle='-', linewidth=2, markersize=4)

        # Настраиваем внешний вид
        plt.title(f'Динамика курса {crypto_name} ({crypto_symbol})')
        plt.xlabel('Дата')
        plt.ylabel('Курс (₽)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)

        # Форматируем оси
        from matplotlib.dates import DateFormatter
        plt.gca().xaxis.set_major_formatter(DateFormatter('%d.%m'))
        plt.tight_layout()

        # Сохраняем график в base64
        import io
        import base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        buf.seek(0)

        # Конвертируем в base64
        graph_base64 = base64.b64encode(buf.getvalue()).decode()
        logger.info("График успешно сгенерирован и конвертирован в base64")
        return graph_base64

    except Exception as e:
        logger.error(f"Ошибка при генерации графика: {e}")
        logger.exception("Полная информация об ошибке:")
        return None

def show_available_cryptos(update: Update, context: CallbackContext):
    """Показывает доступные криптовалюты"""
    logger.info("Вызвана функция show_available_cryptos")

    try:
        # Определяем, был ли это вызван из сообщения или колбэка
        if update.callback_query:
            query = update.callback_query
            query.answer()
            user_id = query.from_user.id
            send_message = query.message.reply_text
        else:
            user_id = update.effective_user.id
            send_message = update.message.reply_text

        user = get_user(user_id)
        if not user:
            logger.warning(f"Неавторизованный доступ от пользователя {user_id}")
            send_message("Сначала необходимо зарегистрироваться!")
            return

        logger.info(f"Получаем список криптовалют для пользователя {user['user_id']}")

        with get_db() as conn:
            cursor = conn.cursor()
            sql_query = """
                SELECT id, name, symbol, rate, available_supply 
                FROM cryptocurrencies 
                WHERE available_supply > 0
                ORDER BY name
            """
            logger.debug(f"Выполняем SQL запрос: {sql_query}")
            cursor.execute(sql_query)
            cryptos = cursor.fetchall()

        if not cryptos:
            logger.warning("Криптовалюты не найдены в базе данных")
            send_message("В данный момент нет доступных криптовалют.")
            return

        logger.info(f"Найдено {len(cryptos)} криптовалют")

        message = "🪙 Доступные криптовалюты:\n\n"
        keyboard = []

        for crypto in cryptos:
            logger.debug(f"Форматирование данных для криптовалюты: {crypto['name']}")
            message += f"{crypto['name']} ({crypto['symbol']}): {format_money(crypto['rate'])}₽\n"
            message += f"Доступно: {format_crypto_amount(crypto['available_supply'])}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"Купить {crypto['symbol']}", 
                callback_data=f"buy_{crypto['id']}"
            )])
            logger.debug(f"Добавлена кнопка покупки для {crypto['symbol']} с callback_data: buy_{crypto['id']}")

        # Добавляем внизу кнопку для просмотра портфеля
        keyboard.append([InlineKeyboardButton("📊 Мой портфель", callback_data="show_portfolio")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        logger.debug(f"Подготовлено сообщение длиной {len(message)} символов и {len(keyboard)} кнопок")

        send_message(message, reply_markup=reply_markup)
        logger.info(f"Информация о криптовалютах успешно отправлена пользователю {user['user_id']}")

    except Exception as e:
        logger.error(f"Ошибка при отображении криптовалют: {str(e)}")
        logger.exception("Полные детали ошибки:")
        if update.callback_query:
            update.callback_query.message.reply_text(
                "Произошла ошибка при получении списка криптовалют. "
                "Пожалуйста, попробуйте позже."
            )
        else:
            update.message.reply_text(
                "Произошла ошибка при получении списка криптовалют. "
                "Пожалуйста, попробуйте позже."
            )