from __future__ import annotations

from datetime import date as Date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ExpenseCategory(str, Enum):
    expense = "expense"
    food = "food"
    vehicle = "vehicle"
    housing = "housing"
    transport = "transport"
    entertainment = "entertainment"
    subscriptions = "subscriptions"
    groceries = "groceries"
    health = "health"


class Currency(str, Enum):
    COP = "COP"
    USD = "USD"
    EUR = "EUR"
    MXN = "MXN"
    ARS = "ARS"
    CLP = "CLP"
    PEN = "PEN"
    BRL = "BRL"


class ParseExpenseRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ParsedExpense(BaseModel):
    id: int = Field(..., ge=1, description="User id extracted from the text.")
    amount: float = Field(..., gt=0)
    date: Date
    category: ExpenseCategory = ExpenseCategory.expense
    description: str | None = None
    currency: Currency | None = None

    model_config = ConfigDict(extra="forbid")


class ExpenseCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    amount: float = Field(..., gt=0)
    date: Date
    category: ExpenseCategory = ExpenseCategory.expense
    currency: Currency = Currency.COP
    description: str | None = None
    payment_method: str | None = None
    note: str | None = None


class ExpenseUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    date: Date | None = None
    category: ExpenseCategory | None = None
    currency: Currency | None = None
    description: str | None = None
    payment_method: str | None = None
    note: str | None = None


class ExpenseRecord(BaseModel):
    id: int
    user_id: int
    amount: float
    date: Date
    category: str
    currency: str = Currency.COP.value
    description: str | None = None
    payment_method: str | None = None
    note: str | None = None
    source: str
    created_at: str


class CategoryRecord(BaseModel):
    id: int
    key: str
    name: str


class IncomeCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    amount: float = Field(..., gt=0)
    currency: Currency = Currency.COP
    date: Date
    source: str = Field(..., min_length=1)
    description: str | None = None


class IncomeRecord(BaseModel):
    id: int
    user_id: int
    amount: float
    currency: str = Currency.COP.value
    date: Date
    source: str
    description: str | None = None
    created_at: str


class BudgetCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    category: ExpenseCategory
    amount: float = Field(..., gt=0)
    currency: Currency = Currency.COP


class BudgetRecord(BaseModel):
    id: int
    user_id: int
    month: str
    category: str
    amount: float
    currency: str = Currency.COP.value
    spent: float = 0

    @computed_field
    @property
    def remaining(self) -> float:
        return round(self.amount - self.spent, 2)

    @computed_field
    @property
    def progress(self) -> float:
        return round(min(self.spent / self.amount, 1), 4) if self.amount else 0


class SavingsGoalCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1)
    target_amount: float = Field(..., gt=0)
    currency: Currency = Currency.COP
    target_date: Date | None = None
    current_amount: float = Field(default=0, ge=0)


class SavingsGoalContribution(BaseModel):
    amount: float = Field(..., gt=0)


class SavingsGoalRecord(BaseModel):
    id: int
    user_id: int
    name: str
    target_amount: float
    currency: str = Currency.COP.value
    target_date: Date | None = None
    current_amount: float
    created_at: str

    @computed_field
    @property
    def progress(self) -> float:
        return round(min(self.current_amount / self.target_amount, 1), 4)


class DashboardSummary(BaseModel):
    user_id: int
    month: str
    total_spent: float
    total_income: float
    balance: float
    currency: str = Currency.COP.value
    previous_month_spent: float
    spent_change_percent: float | None
    spent_by_category: list[dict]
    budgets: list[BudgetRecord]
    recent_expenses: list[ExpenseRecord]


class ApiError(BaseModel):
    error: str
    description: str


class ExpenseResponse(BaseModel):
    expense: ParsedExpense
    db_record: ExpenseRecord


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class UserRecord(BaseModel):
    id: int
    name: str
    email: str
    created_at: str


class UserConfigRecord(BaseModel):
    id: int
    user_id: int
    default_currency: str = Currency.COP.value
    locale: str = "es-CO"
    has_sms_api_key: bool = False
    sms_api_key_suffix: str | None = None
    created_at: str
    updated_at: str


class UserConfigUpdate(BaseModel):
    default_currency: Currency | None = None
    locale: str | None = Field(default=None, min_length=2)


class AuthResponse(BaseModel):
    token: str
    user: UserRecord
    config: UserConfigRecord


class SmsApiKeyResponse(BaseModel):
    api_key: str
    config: UserConfigRecord
