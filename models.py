from pydantic import BaseModel
from typing import Optional
# Shape of data when adding an expense
class Expense(BaseModel):
    title: str
    amount: float
    category: str
    currency: str

class Salary(BaseModel):
    amount: float
    currency: str

class UpdateExpense(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    currency: Optional[str] = None