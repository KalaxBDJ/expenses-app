# Expense Tracker Backend

Small FastAPI backend for parsing expense text with OpenRouter and storing valid expenses in SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your OpenRouter API key in `.env`.

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Endpoints

### SMS Expense Automation

```bash
curl "http://127.0.0.1:8000/sms-expenses/create?text=user%2012%20spent%2018.50%20on%20lunch%20today"
```

Successful responses include the parsed expense and the inserted SQLite record. If the AI cannot detect a user id, or returns invalid data, the API returns an error JSON and does not insert a row.

### Manual Expenses

```bash
curl http://127.0.0.1:8000/categories
```

```bash
curl -X POST http://127.0.0.1:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":18.5,"date":"2026-05-25","category":"food","description":"Lunch","payment_method":"card"}'
```

```bash
curl "http://127.0.0.1:8000/expenses?user_id=1&month=2026-05"
```

### Incomes

```bash
curl -X POST http://127.0.0.1:8000/incomes \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":2500,"date":"2026-05-01","source":"salary"}'
```

### Budgets

```bash
curl -X POST http://127.0.0.1:8000/budgets \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"month":"2026-05","category":"food","amount":400}'
```

### Savings Goals

```bash
curl -X POST http://127.0.0.1:8000/savings-goals \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"name":"Emergency fund","target_amount":1000}'
```

### Monthly Dashboard

```bash
curl "http://127.0.0.1:8000/dashboard/monthly?user_id=1&month=2026-05"
```
