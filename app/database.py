import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from app.auth import create_session_token, hash_password, verify_password
from app.config import settings
from app.schemas import (
    BudgetCreate,
    Currency,
    ExpenseCreate,
    ExpenseRecord,
    IncomeCreate,
    ParsedExpense,
    SavingsGoalCreate,
    UserConfigUpdate,
    UserCreate,
    UserLogin,
)


def _sqlite_path_from_url(database_url: str) -> str:
    if database_url == "sqlite:///:memory:":
        return ":memory:"
    if database_url.startswith("sqlite:///"):
        return database_url.removeprefix("sqlite:///")
    raise ValueError("Only sqlite:/// database URLs are supported right now.")


DB_PATH = _sqlite_path_from_url(settings.database_url)
DEFAULT_CATEGORIES = [
    ("expense", "Expense"),
    ("food", "Food"),
    ("vehicle", "Vehicle"),
    ("housing", "Housing"),
    ("transport", "Transport"),
    ("entertainment", "Entertainment"),
    ("subscriptions", "Subscriptions"),
    ("groceries", "Groceries"),
    ("health", "Health"),
]
DEFAULT_CURRENCY = Currency.COP.value


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    if DB_PATH != ":memory:":
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _expense_table_needs_migration(connection: sqlite3.Connection) -> bool:
    columns = _table_columns(connection, "expenses")
    if not columns:
        return False
    return not {"payment_method", "note", "source", "currency"}.issubset(columns)


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    if column not in _table_columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _create_expenses_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'COP',
            date TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'expense',
            description TEXT,
            payment_method TEXT,
            note TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            raw_text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _migrate_expenses_table(connection: sqlite3.Connection) -> None:
    if not _expense_table_needs_migration(connection):
        return

    connection.execute("ALTER TABLE expenses RENAME TO expenses_old")
    _create_expenses_table(connection)
    connection.execute(
        """
        INSERT INTO expenses (
            id, user_id, amount, currency, date, category, description, raw_text, source, created_at
        )
        SELECT
            id, user_id, amount, 'COP', date, category, description, raw_text, 'sms', created_at
        FROM expenses_old
        """
    )
    connection.execute("DROP TABLE expenses_old")


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                default_currency TEXT NOT NULL DEFAULT 'COP',
                locale TEXT NOT NULL DEFAULT 'es-CO',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        _create_expenses_table(connection)
        _migrate_expenses_table(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.executemany(
            "INSERT OR IGNORE INTO categories (key, name) VALUES (?, ?)",
            DEFAULT_CATEGORIES,
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'COP',
                date TEXT NOT NULL,
                source TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'COP',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, month, category)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'COP',
                target_date TEXT,
                current_amount REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_column_if_missing(connection, "expenses", "currency", "TEXT NOT NULL DEFAULT 'COP'")
        _add_column_if_missing(connection, "incomes", "currency", "TEXT NOT NULL DEFAULT 'COP'")
        _add_column_if_missing(connection, "budgets", "currency", "TEXT NOT NULL DEFAULT 'COP'")
        _add_column_if_missing(connection, "savings_goals", "currency", "TEXT NOT NULL DEFAULT 'COP'")


def _user_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def create_user(user: UserCreate) -> dict:
    normalized_email = user.email.strip().lower()
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (user.name.strip(), normalized_email, hash_password(user.password)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("A user with this email already exists.") from exc
        user_id = cursor.lastrowid
        connection.execute(
            """
            INSERT OR IGNORE INTO user_config (user_id, default_currency, locale)
            VALUES (?, 'COP', 'es-CO')
            """,
            (user_id,),
        )
    return get_user(user_id)


def get_user(user_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return _user_from_row(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, email, password_hash, created_at
            FROM users
            WHERE email = ?
            """,
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def authenticate_user(credentials: UserLogin) -> dict | None:
    user = get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        return None
    token = create_session(user["id"])
    return {"token": token, "user": _user_from_row(user), "config": get_user_config(user["id"])}


def create_session(user_id: int) -> str:
    token = create_session_token()
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO auth_sessions (token, user_id) VALUES (?, ?)",
            (token, user_id),
        )
    return token


def get_user_by_token(token: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT u.id, u.name, u.email, u.created_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    return _user_from_row(row) if row else None


def get_user_config(user_id: int) -> dict:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, user_id, default_currency, locale, created_at, updated_at
            FROM user_config
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if not row:
            connection.execute(
                """
                INSERT INTO user_config (user_id, default_currency, locale)
                VALUES (?, 'COP', 'es-CO')
                """,
                (user_id,),
            )
            row = connection.execute(
                """
                SELECT id, user_id, default_currency, locale, created_at, updated_at
                FROM user_config
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
    return dict(row)


def update_user_config(user_id: int, updates: UserConfigUpdate) -> dict:
    values = updates.model_dump(exclude_unset=True)
    normalized = {
        key: getattr(value, "value", value)
        for key, value in values.items()
        if value is not None and key in {"default_currency", "locale"}
    }
    if not normalized:
        return get_user_config(user_id)

    assignments = ", ".join(f"{key} = ?" for key in normalized)
    params = [*normalized.values(), user_id]
    with get_connection() as connection:
        connection.execute(
            f"""
            UPDATE user_config
            SET {assignments}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            params,
        )
    return get_user_config(user_id)


def _expense_from_row(row: sqlite3.Row) -> dict:
    return dict(row)


def get_expense(expense_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, user_id, amount, date, category, description, payment_method,
                   currency, note, source, created_at
            FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        ).fetchone()
    return _expense_from_row(row) if row else None


def list_categories() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, key, name
            FROM categories
            ORDER BY name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_expense(expense: ExpenseCreate, source: str = "manual", raw_text: str | None = None) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO expenses (
                user_id, amount, currency, date, category, description, payment_method, note, source, raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                expense.user_id,
                expense.amount,
                expense.currency.value,
                expense.date.isoformat(),
                expense.category.value,
                expense.description,
                expense.payment_method,
                expense.note,
                source,
                raw_text,
            ),
        )
        row_id = cursor.lastrowid
    return get_expense(row_id)


def insert_expense(expense: ParsedExpense, raw_text: str) -> dict:
    currency = expense.currency or Currency(get_user_config(expense.id)["default_currency"])
    manual_expense = ExpenseCreate(
        user_id=expense.id,
        amount=expense.amount,
        currency=currency,
        date=expense.date,
        category=expense.category,
        description=expense.description,
    )
    return create_expense(manual_expense, source="sms", raw_text=raw_text)


def list_expenses(
    user_id: int,
    month: str | None = None,
    currency: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = """
        SELECT id, user_id, amount, date, category, description, payment_method,
               currency, note, source, created_at
        FROM expenses
        WHERE user_id = ?
    """
    params: list[object] = [user_id]

    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month)

    if currency:
        query += " AND currency = ?"
        params.append(currency)

    query += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_expense(expense_id: int, updates: dict) -> dict | None:
    allowed = {"amount", "date", "category", "currency", "description", "payment_method", "note"}
    values = {
        key: (value.isoformat() if isinstance(value, date) else getattr(value, "value", value))
        for key, value in updates.items()
        if key in allowed
    }
    if not values:
        return get_expense(expense_id)

    assignments = ", ".join(f"{key} = ?" for key in values)
    params = [*values.values(), expense_id]

    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE expenses SET {assignments} WHERE id = ?",
            params,
        )
        if cursor.rowcount == 0:
            return None
    return get_expense(expense_id)


def delete_expense(expense_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return cursor.rowcount > 0


def create_income(income: IncomeCreate) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO incomes (user_id, amount, currency, date, source, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                income.user_id,
                income.amount,
                income.currency.value,
                income.date.isoformat(),
                income.source,
                income.description,
            ),
        )
        row_id = cursor.lastrowid
        row = connection.execute(
            """
            SELECT id, user_id, amount, currency, date, source, description, created_at
            FROM incomes
            WHERE id = ?
            """,
            (row_id,),
        ).fetchone()
    return dict(row)


def list_incomes(user_id: int, month: str | None = None) -> list[dict]:
    query = """
        SELECT id, user_id, amount, currency, date, source, description, created_at
        FROM incomes
        WHERE user_id = ?
    """
    params: list[object] = [user_id]
    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month)
    query += " ORDER BY date DESC, id DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def upsert_budget(budget: BudgetCreate) -> dict:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO budgets (user_id, month, category, amount, currency)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, month, category) DO UPDATE SET
                amount = excluded.amount,
                currency = excluded.currency
            """,
            (budget.user_id, budget.month, budget.category.value, budget.amount, budget.currency.value),
        )
    return get_budget(budget.user_id, budget.month, budget.category.value)


def get_budget(user_id: int, month: str, category: str) -> dict:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT b.id, b.user_id, b.month, b.category, b.amount, b.currency,
                   COALESCE(SUM(e.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN expenses e
              ON e.user_id = b.user_id
             AND e.category = b.category
             AND strftime('%Y-%m', e.date) = b.month
             AND e.currency = b.currency
            WHERE b.user_id = ? AND b.month = ? AND b.category = ?
            GROUP BY b.id
            """,
            (user_id, month, category),
        ).fetchone()
    return dict(row)


def list_budgets(user_id: int, month: str, currency: str | None = None) -> list[dict]:
    params: list[object] = [user_id, month]
    currency_filter = ""
    if currency:
        currency_filter = "AND b.currency = ?"
        params.append(currency)

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT b.id, b.user_id, b.month, b.category, b.amount, b.currency,
                   COALESCE(SUM(e.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN expenses e
              ON e.user_id = b.user_id
             AND e.category = b.category
             AND strftime('%Y-%m', e.date) = b.month
             AND e.currency = b.currency
            WHERE b.user_id = ? AND b.month = ?
            {currency_filter}
            GROUP BY b.id
            ORDER BY b.category
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def create_savings_goal(goal: SavingsGoalCreate) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO savings_goals (
                user_id, name, target_amount, currency, target_date, current_amount
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                goal.user_id,
                goal.name,
                goal.target_amount,
                goal.currency.value,
                goal.target_date.isoformat() if goal.target_date else None,
                goal.current_amount,
            ),
        )
        row_id = cursor.lastrowid
    return get_savings_goal(row_id)


def get_savings_goal(goal_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, user_id, name, target_amount, currency, target_date, current_amount, created_at
            FROM savings_goals
            WHERE id = ?
            """,
            (goal_id,),
        ).fetchone()
    return dict(row) if row else None


def list_savings_goals(user_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, name, target_amount, currency, target_date, current_amount, created_at
            FROM savings_goals
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def add_savings_goal_contribution(goal_id: int, amount: float) -> dict | None:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE savings_goals
            SET current_amount = current_amount + ?
            WHERE id = ?
            """,
            (amount, goal_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_savings_goal(goal_id)


def get_dashboard_summary(user_id: int, month: str) -> dict:
    month_start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
    previous_month_end = month_start.replace(day=1)
    previous_year = previous_month_end.year
    previous_month = previous_month_end.month - 1
    if previous_month == 0:
        previous_month = 12
        previous_year -= 1
    previous_month_key = f"{previous_year:04d}-{previous_month:02d}"

    currency = get_user_config(user_id)["default_currency"]

    with get_connection() as connection:
        total_spent = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ? AND currency = ?
            """,
            (user_id, month, currency),
        ).fetchone()[0]
        total_income = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM incomes
            WHERE user_id = ? AND strftime('%Y-%m', date) = ? AND currency = ?
            """,
            (user_id, month, currency),
        ).fetchone()[0]
        previous_spent = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ? AND currency = ?
            """,
            (user_id, previous_month_key, currency),
        ).fetchone()[0]
        category_rows = connection.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ? AND currency = ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id, month, currency),
        ).fetchall()

    if previous_spent:
        spent_change_percent = round(((total_spent - previous_spent) / previous_spent) * 100, 2)
    else:
        spent_change_percent = None

    return {
        "user_id": user_id,
        "month": month,
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "balance": round(total_income - total_spent, 2),
        "currency": currency,
        "previous_month_spent": round(previous_spent, 2),
        "spent_change_percent": spent_change_percent,
        "spent_by_category": [dict(row) for row in category_rows],
        "budgets": list_budgets(user_id, month, currency=currency),
        "recent_expenses": list_expenses(user_id=user_id, month=month, currency=currency, limit=8),
    }
