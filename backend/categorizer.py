"""
Categorization pipeline:
  1. Keyword rules (fast, reliable for known merchants)
  2. Semantic fallback via sentence-transformers (Phase 2 — handles unknown merchants)
"""
from nlp_categorizer import semantic_categorize

RULES: list[tuple[str, list[str]]] = [
    ("Food & Dining", ["swiggy", "zomato", "dunzo", "blinkit", "bigbasket", "grofers", "zepto", "instamart", "restaurant", "cafe", "hotel", "dhaba", "kitchen", "food", "aishwarya super", "premaenterprise", "peersab", "mamatha market", "manoj b s"]),
    ("Transport", ["uber", "ola", "rapido", "yulu", "metro", "irctc", "redbus", "makemytrip", "goibibo", "indigo", "spicejet", "air india", "bus", "cab", "taxi", "auto"]),
    ("Shopping", ["amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "snapdeal", "shopsy", "reliance", "dmart"]),
    ("Entertainment", ["netflix", "spotify", "youtube", "hotstar", "zee5", "sonyliv", "prime video", "apple", "bookmyshow", "inox", "pvr", "betterme"]),
    ("Health & Fitness", ["pharmacy", "medplus", "1mg", "netmeds", "apollo", "doctor", "hospital", "clinic", "gym", "cult.fit", "healthkart"]),
    ("Utilities", ["electricity", "airtel", "jio", "vodafone", "bsnl", "tata sky", "dish tv", "recharge", "topup", "gas", "water", "broadband", "wifi"]),
    ("Salary", ["salary", "bajaj finance", "a2aint01"]),
    ("Interest / Returns", ["interest paid", "interest income"]),
    ("Transfer / P2P", ["cred club", "gpay", "phonepe", "paytm", "bharatpe", "mohit", "anand", "divyanshi", "ashish", "ranjan", "jiadul", "mahammad", "salman", "rohit", "dilip", "surendra", "shafiran", "adithya", "malligere", "malappa", "esvarppa", "akbar", "laxmi", "vignesh", "datappa", "shivukumar", "divya d n", "nagaraju", "c ramaiah", "manoj"]),
]

DEFAULT_CATEGORY = "Other"


def _keyword_categorize(text: str) -> str | None:
    for category, keywords in RULES:
        if any(kw in text for kw in keywords):
            return category
    return None


def categorize(merchant: str, narration: str) -> str:
    text = (merchant + " " + narration).lower()

    # Phase 1: keyword rules (fast path)
    result = _keyword_categorize(text)
    if result:
        return result

    # Phase 2: semantic similarity (handles unknown merchants)
    semantic = semantic_categorize(text)
    if semantic:
        return semantic

    return DEFAULT_CATEGORY
