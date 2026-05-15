from pydantic import BaseModel
from typing import Optional, List


class Expense(BaseModel):
    title: str
    amount: float
    category: str
    currency: str


class SmartExpense(BaseModel):
    title: str
    amount: float
    currency: str = "INR"


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
