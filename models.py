from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
import re
from email_validator import validate_email, EmailNotValidError
import phonenumbers

@dataclass
class User:
    user_id: int
    first_name: str
    last_name: str
    middle_name: str
    birth_date: str
    email: str
    phone: str
    balance: float = 0.0
    created_at: datetime = datetime.now()

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Валидация данных пользователя"""
        if not self.first_name or not self.last_name:
            raise ValueError("First name and last name are required")

        # Валидация email
        try:
            validate_email(self.email)
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {str(e)}")

        # Валидация номера телефона
        try:
            phone_number = phonenumbers.parse(self.phone, "RU")
            if not phonenumbers.is_valid_number(phone_number):
                raise ValueError("Invalid phone number")
        except phonenumbers.NumberParseException as e:
            raise ValueError(f"Invalid phone number format: {str(e)}")

        # Валидация даты рождения
        try:
            datetime.strptime(self.birth_date, "%d.%m.%Y")
        except ValueError:
            raise ValueError("Invalid birth date format. Use DD.MM.YYYY")

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name} {self.middle_name}"

@dataclass
class Cryptocurrency:
    id: Optional[int]
    name: str
    symbol: str
    rate: float
    total_supply: float
    available_supply: float

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Валидация данных криптовалюты"""
        if not self.name or len(self.name) < 2:
            raise ValueError("Cryptocurrency name is too short")

        if not re.match(r'^[A-Z]{3}[a-z]$', self.symbol):
            raise ValueError("Symbol must be 3 uppercase letters followed by 1 lowercase letter")

        if self.rate <= 0:
            raise ValueError("Rate must be positive")

        if self.total_supply <= 0:
            raise ValueError("Total supply must be positive")

        if self.available_supply > self.total_supply:
            raise ValueError("Available supply cannot exceed total supply")

    @property
    def market_cap(self) -> float:
        """Расчет рыночной капитализации"""
        return self.rate * self.total_supply

    def __str__(self) -> str:
        return f"{self.name} ({self.symbol}) - {self.rate}₽"

@dataclass
class Portfolio:
    user_id: int
    crypto_id: int
    amount: float

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Валидация данных портфеля"""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

    @property
    def value(self) -> float:
        """Расчет стоимости позиции в портфеле"""
        from database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT rate FROM cryptocurrencies WHERE id = ?',
                (self.crypto_id,)
            )
            result = cursor.fetchone()
            if not result:
                raise ValueError("Cryptocurrency not found")
            rate = result['rate']
            return self.amount * rate

@dataclass
class Transaction:
    id: Optional[int]
    user_id: int
    type: str  # 'deposit' или 'withdraw'
    amount: float
    status: str  # 'pending', 'completed', 'rejected'
    created_at: datetime = datetime.now()

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Валидация данных транзакции"""
        if self.amount <= 0:
            raise ValueError("Transaction amount must be positive")

        valid_types = {'deposit', 'withdraw'}
        if self.type not in valid_types:
            raise ValueError(f"Invalid transaction type. Must be one of: {valid_types}")

        valid_statuses = {'pending', 'completed', 'rejected'}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

    def __str__(self) -> str:
        return f"{self.type.capitalize()}: {self.amount}₽ ({self.status})"

    @property
    def is_pending(self) -> bool:
        return self.status == 'pending'

    @property
    def is_completed(self) -> bool:
        return self.status == 'completed'

    @property
    def formatted_date(self) -> str:
        return self.created_at.strftime('%d.%m.%Y %H:%M')