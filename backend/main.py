import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from categorizer import categorize
from gmail_auth import exchange_code, get_auth_url
from gmail_fetcher import fetch_transactions
from insights import generate_insights
from llm_report import generate_llm_report
from parser import parse_hdfc_pdf

app = FastAPI(title="Smart Spend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_result(transactions: list[dict]) -> dict:
    result = generate_insights(transactions)
    result["transactions"] = transactions
    try:
        result["llm_report"] = generate_llm_report(result)
    except Exception:
        result["llm_report"] = None
    return result


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), password: str = Form("")):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        transactions = parse_hdfc_pdf(tmp_path, password=password)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {str(e)}")
    finally:
        os.unlink(tmp_path)

    if not transactions:
        raise HTTPException(status_code=422, detail="No transactions found in the statement.")

    for t in transactions:
        t["category"] = categorize(t["merchant"], t["narration"])

    return _build_result(transactions)


# ── Gmail endpoints ────────────────────────────────────────────────────────────

@app.get("/auth/gmail-url")
def gmail_auth_url():
    if not os.environ.get("GOOGLE_CLIENT_ID"):
        raise HTTPException(status_code=503, detail="Gmail integration not configured.")
    return {"url": get_auth_url()}


class TokenRequest(BaseModel):
    code: str


@app.post("/auth/gmail/token")
def gmail_token(body: TokenRequest):
    try:
        access_token = exchange_code(body.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")
    return {"access_token": access_token}


class GmailAnalyzeRequest(BaseModel):
    access_token: str


@app.post("/analyze/gmail")
def analyze_gmail(body: GmailAnalyzeRequest):
    try:
        transactions = fetch_transactions(body.access_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch emails: {e}")

    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="No transaction emails found in the last 60 days.",
        )

    return _build_result(transactions)


@app.get("/health")
def health():
    return {"status": "ok"}
