import json
import re

from openai import OpenAI

_CLIENT = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

_SYSTEM = (
    "You are a sharp personal finance analyst. "
    "You receive structured spending data and return concise, specific JSON insights. "
    "Always use ₹ for amounts and be direct."
)

_PROMPT_TEMPLATE = """\
Analyze this bank statement data and return JSON only — no markdown, no extra text.

Spending data:
{data}

Return this exact JSON shape:
{{
  "narrative": "<2–3 sentence summary of the person's spending habits, using specific numbers>",
  "fun_facts": [
    "<surprising or interesting observation 1 with a specific number>",
    "<surprising or interesting observation 2 with a specific number>",
    "<surprising or interesting observation 3 with a specific number>"
  ]
}}"""


def generate_llm_report(insights: dict) -> dict:
    summary = {
        "total_spent": insights["total_spent"],
        "total_received": insights["total_received"],
        "transaction_count": insights["debit_count"],
        "categories": insights["categories"],
        "top_merchant": insights["top_merchant"],
        "biggest_spending_day": insights["biggest_spending_day"],
        "weekend_vs_weekday": insights["weekend_vs_weekday"],
        "spend_by_dow": insights["spend_by_dow"],
    }

    response = _CLIENT.chat.completions.create(
        model="gemma3",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(data=json.dumps(summary, indent=2)),
            },
        ],
        max_tokens=1024,
        temperature=0.7,
    )

    text = response.choices[0].message.content or ""

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"narrative": text.strip(), "fun_facts": []}
