# Expense Tracker Backend

Small FastAPI backend for parsing expense text with OpenRouter and storing valid expenses in SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
cp app/.env.example app/.env
```

Add your OpenRouter API key in `app/.env`.

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000/api`.

## Endpoints

### SMS Expense Automation

Generate an SMS API key from the app settings. Only the last 5 characters are shown after creation, and generating a new key replaces the active one. The API key must be sent in the URL:

```bash
curl "http://127.0.0.1:8000/api/sms-expenses/create?api_key=YOUR_SMS_API_KEY&text=spent%2018.50%20on%20lunch%20today"
```

Successful responses include the parsed expense and the inserted SQLite record. If the API key is missing or invalid, the API returns `401`. The expense is always associated with the user that owns the API key.

### Manual Expenses

```bash
curl http://127.0.0.1:8000/api/categories
```

```bash
curl -X POST http://127.0.0.1:8000/api/expenses \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":18.5,"date":"2026-05-25","category":"food","description":"Lunch","payment_method":"card"}'
```

```bash
curl "http://127.0.0.1:8000/api/expenses?user_id=1&month=2026-05"
```

### Incomes

```bash
curl -X POST http://127.0.0.1:8000/api/incomes \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"amount":2500,"date":"2026-05-01","source":"salary"}'
```

### Budgets

```bash
curl -X POST http://127.0.0.1:8000/api/budgets \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"month":"2026-05","category":"food","amount":400}'
```

### Savings Goals

```bash
curl -X POST http://127.0.0.1:8000/api/savings-goals \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"name":"Emergency fund","target_amount":1000}'
```

### Monthly Dashboard

```bash
curl "http://127.0.0.1:8000/api/dashboard/monthly?user_id=1&month=2026-05"
```
