from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import (
    add_savings_goal_contribution,
    authenticate_user,
    create_expense,
    create_income,
    create_savings_goal,
    create_session,
    create_user,
    delete_expense,
    get_dashboard_summary,
    get_user_by_token,
    get_user_config,
    init_db,
    insert_expense,
    list_budgets,
    list_categories,
    list_expenses,
    list_incomes,
    list_savings_goals,
    update_user_config,
    update_expense,
    upsert_budget,
)
from app.openrouter import OpenRouterError, parse_expense_with_openrouter
from app.schemas import (
    ApiError,
    AuthResponse,
    BudgetCreate,
    BudgetRecord,
    CategoryRecord,
    DashboardSummary,
    ExpenseCreate,
    ExpenseRecord,
    ExpenseResponse,
    ExpenseUpdate,
    IncomeCreate,
    IncomeRecord,
    ParseExpenseRequest,
    SavingsGoalContribution,
    SavingsGoalCreate,
    SavingsGoalRecord,
    UserConfigRecord,
    UserConfigUpdate,
    UserCreate,
    UserLogin,
)


app = FastAPI(title="Expense Tracker API")
security = HTTPBearer(auto_error=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _require_user(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return user


@app.post("/auth/register", response_model=AuthResponse)
def register(user: UserCreate):
    try:
        created = create_user(user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    token = create_session(created["id"])
    return {"token": token, "user": created, "config": get_user_config(created["id"])}


@app.post("/auth/login", response_model=AuthResponse)
def login(credentials: UserLogin):
    session = authenticate_user(credentials)
    if not session:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return session


@app.get("/auth/me", response_model=AuthResponse)
def me(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    user = _require_user(credentials)
    token = credentials.credentials if credentials else ""
    return {"token": token, "user": user, "config": get_user_config(user["id"])}


@app.get("/users/{user_id}/config", response_model=UserConfigRecord)
def read_user_config(user_id: int):
    return get_user_config(user_id)


@app.patch("/users/{user_id}/config", response_model=UserConfigRecord)
def patch_user_config(user_id: int, config: UserConfigUpdate):
    return update_user_config(user_id, config)


@app.get("/categories", response_model=list[CategoryRecord])
def get_categories():
    return list_categories()


@app.post("/expenses", response_model=ExpenseRecord)
def create_manual_expense(expense: ExpenseCreate):
    return create_expense(expense, source="manual")


@app.get("/expenses", response_model=list[ExpenseRecord])
def get_expenses(
    user_id: int = Query(..., ge=1),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return list_expenses(user_id=user_id, month=month, limit=limit, offset=offset)


@app.patch("/expenses/{expense_id}", response_model=ExpenseRecord)
def patch_expense(expense_id: int, expense: ExpenseUpdate):
    updated = update_expense(expense_id, expense.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found.")
    return updated


@app.delete("/expenses/{expense_id}")
def remove_expense(expense_id: int):
    deleted = delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found.")
    return {"deleted": True}


@app.get(
    "/sms-expenses/create",
    response_model=ExpenseResponse,
    responses={400: {"model": ApiError}, 502: {"model": ApiError}},
)
async def create_sms_expense(text: str = Query(..., min_length=1)):
    try:
        request = ParseExpenseRequest(text=text)
        expense = await parse_expense_with_openrouter(request.text)
        db_record = insert_expense(expense, request.text)
    except OpenRouterError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": "expense_parse_failed", "description": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": "expense_insert_failed", "description": str(exc)},
        )

    return {"expense": expense, "db_record": db_record}


@app.post("/incomes", response_model=IncomeRecord)
def add_income(income: IncomeCreate):
    return create_income(income)


@app.get("/incomes", response_model=list[IncomeRecord])
def get_incomes(
    user_id: int = Query(..., ge=1),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    return list_incomes(user_id=user_id, month=month)


@app.post("/budgets", response_model=BudgetRecord)
def save_budget(budget: BudgetCreate):
    return upsert_budget(budget)


@app.get("/budgets", response_model=list[BudgetRecord])
def get_budgets(
    user_id: int = Query(..., ge=1),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
):
    return list_budgets(user_id=user_id, month=month)


@app.post("/savings-goals", response_model=SavingsGoalRecord)
def add_savings_goal(goal: SavingsGoalCreate):
    return create_savings_goal(goal)


@app.get("/savings-goals", response_model=list[SavingsGoalRecord])
def get_savings_goals(user_id: int = Query(..., ge=1)):
    return list_savings_goals(user_id=user_id)


@app.post("/savings-goals/{goal_id}/contributions", response_model=SavingsGoalRecord)
def contribute_to_savings_goal(goal_id: int, contribution: SavingsGoalContribution):
    updated = add_savings_goal_contribution(goal_id, contribution.amount)
    if not updated:
        raise HTTPException(status_code=404, detail="Savings goal not found.")
    return updated


@app.get("/dashboard/monthly", response_model=DashboardSummary)
def monthly_dashboard(
    user_id: int = Query(..., ge=1),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    selected_month = month or date.today().strftime("%Y-%m")
    return get_dashboard_summary(user_id=user_id, month=selected_month)
