import json
from datetime import date

import httpx

from app.config import settings
from app.schemas import ParsedExpense


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(Exception):
    pass


EXPENSE_JSON_SCHEMA = {
    "name": "expense_parse_result",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "amount": {"type": "number", "exclusiveMinimum": 0},
            "currency": {
                "anyOf": [
                    {"type": "string", "enum": ["COP", "USD", "EUR", "MXN", "ARS", "CLP", "PEN", "BRL"]},
                    {"type": "null"},
                ]
            },
            "date": {"type": "string", "format": "date"},
            "category": {
                "type": "string",
                "enum": [
                    "expense",
                    "food",
                    "vehicle",
                    "housing",
                    "transport",
                    "entertainment",
                    "subscriptions",
                    "groceries",
                    "health",
                ],
            },
            "description": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "required": ["amount", "currency", "date", "category", "description"],
    },
}


SYSTEM_PROMPT = """
You extract expense data from user text.

Return only valid JSON matching the schema.
- amount is the expense amount as a number.
- date is ISO format YYYY-MM-DD. If the text omits a date, use today's date provided below.
- currency must be an ISO currency code when clear from the text: COP, USD, EUR, MXN, ARS, CLP, PEN, BRL.
- If the currency is not clear, return currency as null.
- category must be one of: expense, food, vehicle, housing, transport, entertainment, subscriptions, groceries, health.
- Use expense when the text does not clearly match a category.
- description is a short summary when there is enough information, otherwise null.
""".strip()


async def parse_expense_with_openrouter(text: str, user_id: int) -> ParsedExpense:
    if not settings.openrouter_api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_name:
        headers["X-Title"] = settings.openrouter_app_name

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\nToday's date: {date.today().isoformat()}",
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_tokens": settings.openrouter_max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": EXPENSE_JSON_SCHEMA,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                OPENROUTER_CHAT_COMPLETIONS_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        raise OpenRouterError(f"OpenRouter returned {exc.response.status_code}: {body}") from exc
    except httpx.HTTPError as exc:
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    try:
        parsed_json = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter did not return valid JSON.") from exc

    try:
        parsed_json["id"] = user_id
        return ParsedExpense.model_validate(parsed_json)
    except ValueError as exc:
        raise OpenRouterError(f"OpenRouter JSON failed validation: {exc}") from exc
