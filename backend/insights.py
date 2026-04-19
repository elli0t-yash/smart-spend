from collections import defaultdict
from datetime import datetime
from typing import Optional


# ── Personality classification ─────────────────────────────────────────────────

def _classify_personality(
    categories: list[dict],
    weekend_spend: float,
    weekday_spend: float,
    merchant_totals: dict[str, float],
    merchant_counts: dict[str, int],
    total_spent: float,
    debits: list[dict],
) -> list[dict]:
    traits = []
    pct_by_cat = {c["name"]: c["pct"] for c in categories}
    amt_by_cat = {c["name"]: c["amount"] for c in categories}

    food_pct = pct_by_cat.get("Food & Dining", 0)
    if food_pct > 30:
        traits.append({
            "id": "food_heavy",
            "label": "Food-Heavy Spender",
            "description": f"{food_pct:.0f}% of your spending goes to food and dining.",
        })

    shopping_pct = pct_by_cat.get("Shopping", 0)
    if shopping_pct > 25:
        traits.append({
            "id": "shopping_enthusiast",
            "label": "Shopping Enthusiast",
            "description": f"{shopping_pct:.0f}% of your spending goes to online shopping.",
        })

    ent = pct_by_cat.get("Entertainment", 0) + pct_by_cat.get("Utilities", 0)
    if ent > 20:
        ent_amt = amt_by_cat.get("Entertainment", 0) + amt_by_cat.get("Utilities", 0)
        traits.append({
            "id": "subscription_drifter",
            "label": "Subscription Drifter",
            "description": f"₹{ent_amt:,.0f} going to subscriptions and recurring charges.",
        })

    if total_spent > 0:
        weekend_avg = weekend_spend / 2  # 2 weekend days
        weekday_avg = weekday_spend / 5  # 5 weekday days
        if weekend_avg > weekday_avg * 1.5 and weekend_spend > total_spent * 0.3:
            traits.append({
                "id": "weekend_spender",
                "label": "Weekend Spender",
                "description": f"You spend {weekend_avg / weekday_avg:.1f}x more per day on weekends.",
            })

    small_txns = [d for d in debits if d["amount"] < 300]
    if len(small_txns) >= 10 and len(debits) > 0 and len(small_txns) / len(debits) > 0.45:
        traits.append({
            "id": "impulse_spender",
            "label": "Impulse Spender",
            "description": f"{len(small_txns)} transactions under ₹300 — small spends add up.",
        })

    p2p_pct = pct_by_cat.get("Transfer / P2P", 0)
    if p2p_pct > 40:
        traits.append({
            "id": "transfer_heavy",
            "label": "Transfer-Heavy",
            "description": f"{p2p_pct:.0f}% of spending is P2P transfers or shared expenses.",
        })

    if not traits:
        traits.append({
            "id": "controlled_spender",
            "label": "Controlled Spender",
            "description": "Balanced spending with no major outliers — you're doing well.",
        })

    return traits[:2]


# ── Behavior patterns ──────────────────────────────────────────────────────────

def _detect_behavior_patterns(
    debits: list[dict],
    category_totals: dict[str, float],
    merchant_totals: dict[str, float],
    merchant_counts: dict[str, int],
    total_spent: float,
    weekend_spend: float,
    weekday_spend: float,
) -> list[dict]:
    patterns = []

    # Category dominance (skip P2P which is not a "behaviour")
    skip_cats = {"Transfer / P2P", "Salary", "Interest / Returns"}
    for cat, amount in sorted(category_totals.items(), key=lambda x: -x[1]):
        if cat in skip_cats:
            continue
        pct = amount / total_spent * 100 if total_spent else 0
        if pct > 30:
            patterns.append({
                "type": "category_dominance",
                "icon": "📦",
                "title": f"{cat} dominates your spending",
                "detail": f"₹{amount:,.0f} ({pct:.0f}%) of your total spend this period.",
            })
            break

    # Weekend spike
    if total_spent > 0:
        weekend_avg = weekend_spend / 2
        weekday_avg = weekday_spend / 5 if weekday_spend else 1
        if weekend_avg > weekday_avg * 1.5:
            ratio = weekend_avg / weekday_avg
            patterns.append({
                "type": "weekend_spike",
                "icon": "📅",
                "title": "Weekend spending spikes",
                "detail": f"You spend {ratio:.1f}x more per day on weekends (₹{weekend_spend:,.0f} vs ₹{weekday_spend:,.0f} weekdays).",
            })

    # Merchant addiction — one merchant > 20% of spend
    if total_spent > 0:
        for merchant, amount in sorted(merchant_totals.items(), key=lambda x: -x[1]):
            pct = amount / total_spent * 100
            if pct > 20:
                count = merchant_counts.get(merchant, 1)
                patterns.append({
                    "type": "merchant_addiction",
                    "icon": "📍",
                    "title": f"Heavy reliance on {merchant}",
                    "detail": f"₹{amount:,.0f} ({pct:.0f}%) across {count} transactions.",
                })
                break

    # Shopping bursts — check if most shopping is concentrated in few days
    shopping_by_date: dict[str, float] = defaultdict(float)
    for d in debits:
        if d.get("category") == "Shopping":
            shopping_by_date[d["date"]] += d["amount"]
    if len(shopping_by_date) > 0:
        shopping_total = sum(shopping_by_date.values())
        max_day_amt = max(shopping_by_date.values())
        if shopping_total > 0 and max_day_amt / shopping_total > 0.5:
            patterns.append({
                "type": "shopping_burst",
                "icon": "🛒",
                "title": "Shopping concentrated in one day",
                "detail": f"₹{max_day_amt:,.0f} of your shopping happened in a single session.",
            })

    return patterns


# ── Money leakage ──────────────────────────────────────────────────────────────

def _detect_leakage(
    debits: list[dict],
    merchant_totals: dict[str, float],
    merchant_counts: dict[str, int],
) -> list[dict]:
    leakages = []

    # Frequent small spends (< ₹300)
    small = [d for d in debits if d["amount"] < 300]
    if small:
        total_small = sum(d["amount"] for d in small)
        leakages.append({
            "type": "small_spends",
            "icon": "🪙",
            "title": f"{len(small)} micro-transactions",
            "detail": f"Totaling ₹{total_small:,.0f} — individually small, collectively significant.",
            "amount": round(total_small, 2),
        })

    # Repeat merchants (5+ transactions)
    repeat = [
        (m, merchant_counts[m], merchant_totals[m])
        for m in merchant_counts
        if merchant_counts[m] >= 5
    ]
    repeat.sort(key=lambda x: -x[2])
    for merchant, count, amount in repeat[:2]:
        leakages.append({
            "type": "repeat_merchant",
            "icon": "🔁",
            "title": f"{merchant} — {count} transactions",
            "detail": f"₹{amount:,.0f} total. That's ₹{amount / count:,.0f} per visit on average.",
            "amount": round(amount, 2),
        })

    return leakages


# ── Suggestions ────────────────────────────────────────────────────────────────

def _generate_suggestions(
    behavior_patterns: list[dict],
    leakage: list[dict],
    categories: list[dict],
    merchant_totals: dict[str, float],
    merchant_counts: dict[str, int],
    total_spent: float,
) -> list[dict]:
    suggestions = []
    pattern_types = {p["type"] for p in behavior_patterns}
    leakage_types = {l["type"] for l in leakage}
    cat_pcts = {c["name"]: c["pct"] for c in categories}
    cat_amts = {c["name"]: c["amount"] for c in categories}

    food_pct = cat_pcts.get("Food & Dining", 0)
    if food_pct > 25:
        food_amt = cat_amts.get("Food & Dining", 0)
        save = round(food_amt * 0.3 / 100) * 100
        suggestions.append({
            "icon": "🍳",
            "text": f"Cooking 2–3 meals a week could save ~₹{save:,.0f}/month on food.",
        })

    if "weekend_spike" in pattern_types:
        suggestions.append({
            "icon": "📋",
            "text": "Set a fixed weekend budget and pay with cash — it makes overspending feel real.",
        })

    if "merchant_addiction" in pattern_types:
        top_m, top_amt = max(merchant_totals.items(), key=lambda x: x[1])
        count = merchant_counts.get(top_m, 1)
        save = round(top_amt * 0.4 / 100) * 100
        suggestions.append({
            "icon": "🎯",
            "text": f"Cap {top_m} to {max(1, count // 2)}x/week — could save ~₹{save:,.0f}/month.",
        })

    if "small_spends" in leakage_types:
        small_l = next(l for l in leakage if l["type"] == "small_spends")
        suggestions.append({
            "icon": "💡",
            "text": f"Audit those {small_l['title'].split()[0]} micro-spends — ₹{small_l['amount']:,.0f} in small purchases is easy to overlook.",
        })

    if "repeat_merchant" in leakage_types:
        r = next(l for l in leakage if l["type"] == "repeat_merchant")
        save = round(r["amount"] * 0.5 / 100) * 100
        merchant_name = r["title"].split("—")[0].strip()
        suggestions.append({
            "icon": "✂️",
            "text": f"Halving your {merchant_name} orders could save ~₹{save:,.0f} this month.",
        })

    shopping_pct = cat_pcts.get("Shopping", 0)
    if shopping_pct > 20:
        suggestions.append({
            "icon": "🛒",
            "text": "Add items to cart and wait 24 hours before buying — kills impulse purchases.",
        })

    return suggestions[:4]


# ── Spending score ─────────────────────────────────────────────────────────────

def _compute_spending_score(
    total_spent: float,
    total_received: float,
    categories: list[dict],
    weekend_spend: float,
    weekday_spend: float,
    debits: list[dict],
) -> dict:
    score = 10.0

    # Savings rate (-3 max)
    if total_received > 0:
        savings_rate = (total_received - total_spent) / total_received
        if savings_rate < 0:
            score -= 3
        elif savings_rate < 0.10:
            score -= 2
        elif savings_rate < 0.20:
            score -= 1

    # Food % (-2 max)
    food_pct = next((c["pct"] for c in categories if c["name"] == "Food & Dining"), 0)
    if food_pct > 40:
        score -= 2
    elif food_pct > 30:
        score -= 1
    elif food_pct > 20:
        score -= 0.5

    # Weekend spike (-1.5 max)
    weekend_avg = weekend_spend / 2
    weekday_avg = weekday_spend / 5 if weekday_spend else 0
    if weekday_avg > 0:
        if weekend_avg > weekday_avg * 2:
            score -= 1.5
        elif weekend_avg > weekday_avg * 1.5:
            score -= 0.5

    # Impulse spends (-1.5 max)
    if debits:
        small_ratio = sum(1 for d in debits if d["amount"] < 300) / len(debits)
        if small_ratio > 0.6:
            score -= 1.5
        elif small_ratio > 0.4:
            score -= 0.5

    score = round(max(1.0, min(10.0, score)), 1)

    if score >= 8.5:
        label = "Excellent"
    elif score >= 7.0:
        label = "Good"
    elif score >= 5.5:
        label = "Average"
    else:
        label = "Needs Work"

    return {"score": score, "label": label}


# ── Smart alert ────────────────────────────────────────────────────────────────

def _generate_smart_alert(
    weekend_spend: float,
    weekday_spend: float,
    total_spent: float,
    total_received: float,
    merchant_totals: dict[str, float],
) -> Optional[str]:
    weekend_avg = weekend_spend / 2
    weekday_avg = weekday_spend / 5 if weekday_spend else 0

    if weekday_avg > 0 and weekend_avg > weekday_avg * 2:
        ratio = weekend_avg / weekday_avg
        return f"You spent {ratio:.1f}x more per day on weekends than weekdays."

    if total_received > 0 and total_spent > total_received:
        excess = total_spent - total_received
        return f"You spent ₹{excess:,.0f} more than you earned this period."

    if total_spent > 0 and merchant_totals:
        top_m, top_amt = max(merchant_totals.items(), key=lambda x: x[1])
        pct = top_amt / total_spent * 100
        if pct > 25:
            return f"{top_m} alone accounts for {pct:.0f}% of your total spending."

    return None


# ── Biggest leak ───────────────────────────────────────────────────────────────

_SKIP_LEAK_CATS = {"Transfer / P2P", "Salary", "Interest / Returns"}

def _find_biggest_leak(
    debits: list[dict],
    merchant_totals: dict[str, float],
    merchant_counts: dict[str, int],
    total_spent: float,
) -> Optional[dict]:
    # Top merchant excluding internal/salary categories
    candidates = [
        (m, amt)
        for m, amt in merchant_totals.items()
        if not any(
            d["merchant"] == m and d.get("category", "") in _SKIP_LEAK_CATS
            for d in debits
        )
    ]
    if not candidates:
        return None
    top_m, top_amt = max(candidates, key=lambda x: x[1])
    return {
        "merchant": top_m,
        "amount": round(top_amt, 2),
        "count": merchant_counts.get(top_m, 0),
        "pct": round(top_amt / total_spent * 100, 1) if total_spent else 0,
    }


# ── Main entry point ───────────────────────────────────────────────────────────

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
        {
            "name": k,
            "amount": round(v, 2),
            "count": category_counts[k],
            "pct": round(v / total_spent * 100, 1) if total_spent else 0,
        }
        for k, v in sorted(category_totals.items(), key=lambda x: -x[1])
    ]

    # Merchant aggregation
    merchant_totals: dict[str, float] = defaultdict(float)
    merchant_counts: dict[str, int] = defaultdict(int)
    for t in debits:
        merchant_totals[t["merchant"]] += t["amount"]
        merchant_counts[t["merchant"]] += 1

    top_merchant = max(merchant_totals.items(), key=lambda x: x[1], default=("N/A", 0))

    # Day-of-week breakdown
    dow_totals: dict[str, float] = defaultdict(float)
    dow_counts: dict[str, int] = defaultdict(int)
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for t in debits:
        dow = datetime.fromisoformat(t["date"]).weekday()
        dow_totals[dow_names[dow]] += t["amount"]
        dow_counts[dow_names[dow]] += 1

    # Biggest single day
    date_totals: dict[str, float] = defaultdict(float)
    for t in debits:
        date_totals[t["date"]] += t["amount"]
    biggest_day = max(date_totals.items(), key=lambda x: x[1], default=("N/A", 0))

    weekend_spend = sum(v for k, v in dow_totals.items() if k in ("Saturday", "Sunday"))
    weekday_spend = total_spent - weekend_spend

    # Savings
    savings = round(total_received - total_spent, 2)
    savings_rate = round(savings / total_received * 100, 1) if total_received else 0

    # Behavioural analysis
    personality = _classify_personality(
        categories, weekend_spend, weekday_spend,
        merchant_totals, merchant_counts, total_spent, debits,
    )
    behavior_patterns = _detect_behavior_patterns(
        debits, category_totals, merchant_totals, merchant_counts,
        total_spent, weekend_spend, weekday_spend,
    )
    leakage = _detect_leakage(debits, merchant_totals, merchant_counts)
    suggestions = _generate_suggestions(
        behavior_patterns, leakage, categories,
        merchant_totals, merchant_counts, total_spent,
    )
    spending_score = _compute_spending_score(
        total_spent, total_received, categories,
        weekend_spend, weekday_spend, debits,
    )
    smart_alert = _generate_smart_alert(
        weekend_spend, weekday_spend, total_spent,
        total_received, merchant_totals,
    )
    biggest_leak = _find_biggest_leak(debits, merchant_totals, merchant_counts, total_spent)

    # Legacy insight cards (kept for compatibility)
    cards = _build_cards(
        total_spent, total_received, categories, top_merchant,
        biggest_day, weekend_spend, weekday_spend, dow_totals, debits,
    )

    return {
        "total_spent": round(total_spent, 2),
        "total_received": round(total_received, 2),
        "savings": savings,
        "savings_rate": savings_rate,
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
        "personality": personality,
        "behavior_patterns": behavior_patterns,
        "leakage": leakage,
        "suggestions": suggestions,
        "spending_score": spending_score,
        "smart_alert": smart_alert,
        "biggest_leak": biggest_leak,
    }


def _build_cards(
    total_spent, total_received, categories, top_merchant,
    biggest_day, weekend_spend, weekday_spend, dow_totals, debits,
) -> list[dict]:
    cards = []

    if categories:
        top_cat = categories[0]
        cards.append({
            "title": f"{top_cat['name']} is your biggest expense",
            "body": f"You spent ₹{top_cat['amount']:,.0f} on {top_cat['name'].lower()} — {top_cat['pct']}% of your total spending.",
            "icon": "🏆",
        })

    if weekend_spend + weekday_spend > 0:
        weekend_pct = round(weekend_spend / (weekend_spend + weekday_spend) * 100)
        if weekend_pct > 40:
            cards.append({
                "title": "You spend more on weekends",
                "body": f"{weekend_pct}% of your spending (₹{weekend_spend:,.0f}) happened on weekends.",
                "icon": "📅",
            })
        else:
            cards.append({
                "title": "Most spending happens on weekdays",
                "body": f"Weekday spend was ₹{weekday_spend:,.0f} vs ₹{weekend_spend:,.0f} on weekends.",
                "icon": "📅",
            })

    if top_merchant[1] > 0:
        cards.append({
            "title": f"Most paid to: {top_merchant[0]}",
            "body": f"You transferred the most to {top_merchant[0]} — ₹{top_merchant[1]:,.0f} total.",
            "icon": "💸",
        })

    if biggest_day[1] > 0:
        try:
            date_fmt = datetime.fromisoformat(biggest_day[0]).strftime("%d %b %Y")
        except Exception:
            date_fmt = biggest_day[0]
        cards.append({
            "title": "Biggest spending day",
            "body": f"You spent ₹{biggest_day[1]:,.0f} on {date_fmt} — your highest single-day outflow.",
            "icon": "📈",
        })

    p2p = next((c for c in categories if c["name"] == "Transfer / P2P"), None)
    if p2p and p2p["pct"] > 30:
        cards.append({
            "title": "Large transfers this month",
            "body": f"₹{p2p['amount']:,.0f} ({p2p['pct']}%) went to personal transfers or P2P payments.",
            "icon": "🔄",
        })

    return cards
