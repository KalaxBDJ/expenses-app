import json
import re
from datetime import date

import httpx

from app.config import settings
from app.schemas import ParsedExpense


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(Exception):
    pass


class EmptyOpenRouterResponse(OpenRouterError):
    pass


class InvalidOpenRouterJson(OpenRouterError):
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
Do not include reasoning, analysis, markdown, or explanations.
- amount is the expense amount as a number.
- date is ISO format YYYY-MM-DD. If the text omits a date, use today's date provided below.
- If the text has a date like DD/MM, infer the year from today's date and return YYYY-MM-DD.
- currency must be an ISO currency code when clear from the text: COP, USD, EUR, MXN, ARS, CLP, PEN, BRL.
- A text like "Transferiste", "Pagaste", "Compraste", "Retiraste", or "desde tu cuenta" is an expense.
- If the currency is not clear, return currency as null.
- category must be one of: expense, food, vehicle, housing, transport, entertainment, subscriptions, groceries, health.
- Use expense when the text does not clearly match a category.
- description is a short summary when there is enough information, otherwise null.
""".strip()


def _json_object_from_text(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _extract_message_content(data: dict) -> str:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise EmptyOpenRouterResponse("OpenRouter response did not include a message.") from exc

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        text = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        ).strip()
        if text:
            return text

    finish_reason = data.get("choices", [{}])[0].get("finish_reason")
    raise EmptyOpenRouterResponse(f"OpenRouter returned an empty response. finish_reason={finish_reason}")


async def _request_openrouter(payload: dict, headers: dict) -> dict:
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

    return response.json()


def _parse_openrouter_json(data: dict) -> dict:
    content = _extract_message_content(data)
    try:
        parsed_json = json.loads(_json_object_from_text(content))
    except json.JSONDecodeError as exc:
        preview = content[:240].replace("\n", " ")
        raise InvalidOpenRouterJson(f"OpenRouter did not return valid JSON. content={preview!r}") from exc
    if not isinstance(parsed_json, dict):
        raise InvalidOpenRouterJson("OpenRouter JSON response was not an object.")
    return parsed_json


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

    messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\nToday's date: {date.today().isoformat()}",
        },
        {"role": "user", "content": text},
    ]

    max_tokens = max(settings.openrouter_max_tokens, 2500)

    payload = {
        "model": settings.openrouter_model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": EXPENSE_JSON_SCHEMA,
        },
    }

    try:
        parsed_json = _parse_openrouter_json(await _request_openrouter(payload, headers))
    except (EmptyOpenRouterResponse, InvalidOpenRouterJson):
        fallback_payload = {
            "model": settings.openrouter_model,
            "messages": [
                *messages,
                {
                    "role": "system",
                    "content": (
                        "Return a raw JSON object only. Do not include markdown, commentary, or reasoning. "
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": max(max_tokens, 4000),
        }
        parsed_json = _parse_openrouter_json(await _request_openrouter(fallback_payload, headers))

    try:
        parsed_json["id"] = user_id
        return ParsedExpense.model_validate(parsed_json)
    except ValueError as exc:
        raise OpenRouterError(f"OpenRouter JSON failed validation: {exc}") from exc
