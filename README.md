# Smart Spend

Upload your HDFC bank statement (PDF) or connect Gmail to get an instant breakdown of your spending — categorized transactions, summary stats, and an AI-generated insights report.

## What it does

- Parses HDFC bank statement PDFs (password-protected supported)
- Fetches transaction emails from Gmail (last 60 days)
- Categorizes transactions automatically
- Generates spending insights and an LLM-written summary report
- Visualizes results in a Next.js frontend with charts

## Stack

- **Frontend**: Next.js 16, React 19, Tailwind CSS, Recharts
- **Backend**: FastAPI (Python), pdfplumber, OpenAI API

## Prerequisites

- Node.js 18+
- Python 3.11+
- An OpenAI API key
- (Optional) Google OAuth credentials for Gmail integration

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
OPENAI_API_KEY=sk-...

# Optional — only needed for Gmail integration
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback
```

Start the API server:

```bash
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:3000`.

## Usage

1. Open `http://localhost:3000`
2. Upload an HDFC bank statement PDF, or connect Gmail
3. View categorized transactions, charts, and the AI report
