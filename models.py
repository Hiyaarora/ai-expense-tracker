from pydantic import BaseModel
from typing import Optional, List


class Expense(BaseModel):
    title: str
    amount: float
    category: str
    currency: str
    date: Optional[str] = None  # ISO format YYYY-MM-DD, defaults to today


class SmartExpense(BaseModel):
    title: str
    amount: float
    currency: str = "INR"
    date: Optional[str] = None  # ISO format YYYY-MM-DD, defaults to today


class NaturalExpense(BaseModel):
    text: str
    date: Optional[str] = None  # ISO format YYYY-MM-DD, defaults to today


class Salary(BaseModel):
    amount: float
    currency: str


class UpdateExpense(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    currency: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


class SettingsUpdate(BaseModel):
    base_currency: str  # e.g. "INR", "USD", "EUR"
