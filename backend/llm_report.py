import json
import re

from openai import OpenAI

_CLIENT = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

_SYSTEM = (
    "You are a sharp behavioral finance analyst. "
    "You receive structured spending data and return concise, specific JSON insights. "
    "Focus on behavior — patterns, habits, and what the numbers reveal about the person. "
    "Always use ₹ for amounts. Be direct, specific, and avoid generic advice."
)

_PROMPT_TEMPLATE = """\
Analyze this spending behavior data and return JSON only — no markdown, no extra text.

Data:
{data}

Return this exact JSON shape:
{{
  "narrative": "<2–3 sentences describing this person's spending behavior using specific numbers. Mention their dominant pattern, a surprising observation, and one concrete implication.>",
  "fun_facts": [
    "<specific behavioral observation 1 with a number — e.g. frequency, ratio, or comparison>",
    "<specific behavioral observation 2 with a number>",
    "<specific behavioral observation 3 with a number>"
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
        "personality": insights.get("personality", []),
        "behavior_patterns": insights.get("behavior_patterns", []),
        "leakage": insights.get("leakage", []),
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
