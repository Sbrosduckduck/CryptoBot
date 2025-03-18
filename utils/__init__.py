"""
Utility package for the Telegram bot.
"""

import logging
from typing import Union, List, Dict, Optional
from datetime import datetime
import re
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from config import ADMIN_EMAIL, ADMIN_IDS, MIN_AMOUNT

def is_admin(user: Union[int, dict]) -> bool:
    """
    Проверяет, является ли пользователь администратором
    :param user: ID пользователя (int) или словарь с данными пользователя
    :return: True если пользователь админ, False в противном случае
    """
    try:
        # Если передан ID пользователя
        if isinstance(user, (int, str)):
            # Проверяем сначала по списку админских ID
            if int(user) in ADMIN_IDS:
                logging.info(f"User {user} is admin (by ID)")
                return True

            # Если нет в списке ID, проверяем email
            from database import get_user
            user_data = get_user(int(user))
            if user_data and user_data.get('email') == ADMIN_EMAIL:
                logging.info(f"User {user} is admin (by email)")
                return True

        # Если передан словарь с данными пользователя
        elif isinstance(user, dict):
            # Проверяем ID
            if user.get('user_id') in ADMIN_IDS:
                logging.info(f"User {user.get('user_id')} is admin (by ID)")
                return True

            # Проверяем email
            if user.get('email') == ADMIN_EMAIL:
                logging.info(f"User {user.get('user_id')} is admin (by email)")
                return True

        return False

    except Exception as e:
        logging.error(f"Error in is_admin check: {str(e)}")
        return False

def validate_email_address(email: str) -> bool:
    """Проверяет корректность email"""
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

def validate_phone_number(phone: str) -> bool:
    """Проверяет корректность телефона"""
    try:
        parsed_number = phonenumbers.parse(phone, "RU")
        return phonenumbers.is_valid_number(parsed_number)
    except:
        return False

def validate_date(date_str: str) -> bool:
    """Проверяет корректность даты"""
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False

def format_money(amount: float) -> str:
    """Форматирует денежную сумму"""
    return f"{amount:,.2f} ₽"

def format_crypto_amount(amount: float) -> str:
    """Форматирует сумму криптовалюты"""
    if amount >= 1:
        return f"{amount:.8f}"
    else:
        return f"{amount:.12f}"

def generate_price_chart(price_history: List[Dict], crypto_symbol: str) -> Optional[str]:
    """
    Генерирует график изменения цены криптовалюты
    :param price_history: Список записей истории цен
    :param crypto_symbol: Символ криптовалюты для отображения
    :return: Строка с данными изображения в формате base64 или None в случае ошибки
    """
    try:
        import os
        import base64
        from io import BytesIO
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        if not price_history or len(price_history) < 2:
            return None

        # Создаем директорию для сохранения графиков, если её нет
        os.makedirs('static/charts', exist_ok=True)

        # Подготавливаем данные
        dates = [datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) 
                if 'Z' in entry['timestamp'] else datetime.fromisoformat(entry['timestamp']) 
                for entry in price_history]
        prices = [entry['rate'] for entry in price_history]

        # Определяем изменение цены (в процентах)
        if len(prices) >= 2:
            price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
        else:
            price_change = 0

        # Создаем график
        plt.figure(figsize=(10, 5))
        plt.plot(dates, prices, marker='o', linestyle='-', color='#3273a8')

        # Настраиваем формат оси X
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

        # Добавляем заголовок и подписи осей
        plt.title(f'Изменение курса {crypto_symbol} ({price_change:.2f}%)', fontsize=14)
        plt.ylabel('Цена (₽)', fontsize=12)
        plt.xlabel('Дата', fontsize=12)

        # Заливка под графиком
        plt.fill_between(dates, prices, alpha=0.2, color='#3273a8')

        # Изменение цвета в зависимости от тренда
        if price_change > 0:
            plt.fill_between(dates, prices, alpha=0.2, color='green')
        elif price_change < 0:
            plt.fill_between(dates, prices, alpha=0.2, color='red')

        # Добавляем сетку
        plt.grid(True, linestyle='--', alpha=0.7)

        # Устанавливаем отступы
        plt.tight_layout()

        # Сохраняем график в BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=80)
        plt.close()

        # Кодируем в base64
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return image_base64
    except Exception as e:
        logging.error(f"Error generating price chart: {e}")
        return None
