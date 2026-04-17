from collections import defaultdict
from datetime import datetime


def generate_insights(transactions: list[dict]) -> dict:
    debits = [t for t in transactions if t["type"] == "debit"]
    credits = [t for t in transactions if t["type"] == "credit"]

    total_spent = sum(t["amount"] for t in debits)
    total_received = sum(t["amount"] for t in credits)

    # Category breakdown
    category_totals: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    for t in debits:
        category_totals[t["category"]] += t["amount"]
        category_counts[t["category"]] += 1

    categories = [
        {"name": k, "amount": round(v, 2), "count": category_counts[k], "pct": round(v / total_spent * 100, 1) if total_spent else 0}
        for k, v in sorted(category_totals.items(), key=lambda x: -x[1])
    ]

    # Top merchant
    merchant_totals: dict[str, float] = defaultdict(float)
    for t in debits:
        merchant_totals[t["merchant"]] += t["amount"]
    top_merchant = max(merchant_totals.items(), key=lambda x: x[1], default=("N/A", 0))

    # Spending by day of week
    dow_totals: dict[str, float] = defaultdict(float)
    dow_counts: dict[str, int] = defaultdict(int)
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for t in debits:
        dow = datetime.fromisoformat(t["date"]).weekday()
        dow_totals[dow_names[dow]] += t["amount"]
        dow_counts[dow_names[dow]] += 1

    # Highest spending day (date)
    date_totals: dict[str, float] = defaultdict(float)
    for t in debits:
        date_totals[t["date"]] += t["amount"]
    biggest_day = max(date_totals.items(), key=lambda x: x[1], default=("N/A", 0))

    # Weekend vs weekday
    weekend_spend = sum(v for k, v in dow_totals.items() if k in ("Saturday", "Sunday"))
    weekday_spend = total_spent - weekend_spend

    # Build insight cards
    cards = _build_cards(
        total_spent, total_received, categories, top_merchant,
        biggest_day, weekend_spend, weekday_spend, dow_totals, debits
    )

    return {
        "total_spent": round(total_spent, 2),
        "total_received": round(total_received, 2),
        "debit_count": len(debits),
        "credit_count": len(credits),
        "categories": categories,
        "top_merchant": {"name": top_merchant[0], "amount": round(top_merchant[1], 2)},
        "biggest_spending_day": {"date": biggest_day[0], "amount": round(biggest_day[1], 2)},
        "weekend_vs_weekday": {
            "weekend": round(weekend_spend, 2),
            "weekday": round(weekday_spend, 2),
        },
        "spend_by_dow": [{"day": d, "amount": round(dow_totals.get(d, 0), 2)} for d in dow_names],
        "insights": cards,
    }


def _build_cards(
    total_spent, total_received, categories, top_merchant,
    biggest_day, weekend_spend, weekday_spend, dow_totals, debits
) -> list[dict]:
    cards = []

    # Top category insight
    if categories:
        top_cat = categories[0]
        cards.append({
            "title": f"{top_cat['name']} is your biggest expense",
            "body": f"You spent ₹{top_cat['amount']:,.0f} on {top_cat['name'].lower()} — {top_cat['pct']}% of your total spending this month.",
            "icon": "🏆",
        })

    # Weekend vs weekday
    if weekend_spend + weekday_spend > 0:
        weekend_pct = round(weekend_spend / (weekend_spend + weekday_spend) * 100)
        if weekend_pct > 40:
            cards.append({
                "title": "You spend more on weekends",
                "body": f"{weekend_pct}% of your spending (₹{weekend_spend:,.0f}) happened on weekends. Weekday spend was ₹{weekday_spend:,.0f}.",
                "icon": "📅",
            })
        else:
            cards.append({
                "title": "Most spending happens on weekdays",
                "body": f"Weekday spend was ₹{weekday_spend:,.0f} vs ₹{weekend_spend:,.0f} on weekends.",
                "icon": "📅",
            })

    # Top merchant
    if top_merchant[1] > 0:
        cards.append({
            "title": f"Most paid to: {top_merchant[0]}",
            "body": f"You transferred the most money to {top_merchant[0]} this month — ₹{top_merchant[1]:,.0f} total.",
            "icon": "💸",
        })

    # Biggest day
    if biggest_day[1] > 0:
        try:
            date_fmt = datetime.fromisoformat(biggest_day[0]).strftime("%d %b %Y")
        except Exception:
            date_fmt = biggest_day[0]
        cards.append({
            "title": "Biggest spending day",
            "body": f"You spent ₹{biggest_day[1]:,.0f} on {date_fmt} — your highest single-day outflow this month.",
            "icon": "📈",
        })

    # Transfer/P2P heavy
    p2p = next((c for c in categories if c["name"] == "Transfer / P2P"), None)
    if p2p and p2p["pct"] > 30:
        cards.append({
            "title": "Large transfers this month",
            "body": f"₹{p2p['amount']:,.0f} ({p2p['pct']}%) went to personal transfers or P2P payments. These may include rent, shared expenses, or lending.",
            "icon": "🔄",
        })

    return cards
