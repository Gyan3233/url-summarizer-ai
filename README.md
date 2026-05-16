# 🧠 AI Document & URL Analyst — v3.0

GenAI-powered platform for URL summarisation, document comparison, Power BI analytics, and document chat (RAG).
Runs on Docker Desktop. Deployed on Streamlit Cloud. Free with Groq API.

---

## What's new in v3.0

| Mode | What it does |
|---|---|
| 📄 Summarize URLs | Paste 1+ URLs → AI summaries in 8 languages, 5 styles |
| ⚖️ Compare & Rank | URLs **or uploaded documents** → side-by-side + differences + ranked winner |
| 📊 Power BI Analyst | Paste KPIs → ask questions, KPI health check, period comparison, written report |
| 🧠 Document Chat (RAG) | Upload PDF/DOCX/TXT → chat with your documents using AI |

---

## Project structure

```
url_summarizer/
├── app.py                ← Full application (all 4 modes)
├── Dockerfile            ← Updated for v3.0 (build tools + libgl1)
├── docker-compose.yml    ← One-command run
├── requirements.txt      ← All dependencies including RAG stack
├── .env.example          ← Copy to .env and add your key
├── .gitignore            ← Keeps .env out of Git
└── .streamlit/
    └── config.toml       ← Dark theme + server settings
```

---

## Quick start (3 steps)

### Step 1 — Get free Groq API key
→ https://console.groq.com → Sign up → API Keys → Create Key

### Step 2 — Create .env file
```
GROQ_API_KEY=gsk_your_actual_key_here
```

### Step 3 — Run
```bash
docker-compose up --build
```

Open browser → http://localhost:8501

> **Note:** First build takes 5–8 minutes in v3.0 because
> sentence-transformers and faiss compile native extensions.
> Every subsequent run starts in under 15 seconds.

---

## Enterprise use cases (Mode 2 — Compare & Rank)

Pick a department template before uploading documents:

| Department | Template does |
|---|---|
| HR | Rank candidates, highlight skill gaps |
| Legal | Extract clauses, flag risks |
| Finance | Summarise financials, highlight KPIs |
| Procurement | Score vendors, recommend winner |
| Sales | Extract RFP requirements, draft outline |
| SAP | Scope, gaps, integration points |

---

## Document Chat (Mode 4 — RAG)

1. Upload one or more PDF / DOCX / TXT files
2. Click **Build index & start chat**
3. Ask any question — answers are grounded in your documents only

**Accuracy by document type:**

| Document type | Accuracy |
|---|---|
| Text-based PDF / DOCX | 85–95% |
| Financial reports with tables | 70–80% |
| Scanned / image PDFs | 60–75% (needs OCR) |

---

## Stop the app
```bash
docker-compose down
```

## Rebuild after code changes
```bash
docker-compose down
docker-compose up --build
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Build takes too long | Normal on first run — sentence-transformers is large (~500MB) |
| Port 8501 in use | Change `8501:8501` → `8502:8501` in docker-compose.yml |
| API key error | Check .env — no quotes around the value |
| PDF not parsing | Make sure it is text-based, not a scanned image |
| RAG gives wrong answer | Ask more specific questions; vague questions reduce accuracy |

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | Groq — Llama 3.3 70B (free) |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 (local, free) |
| Vector search | FAISS in-memory |
| RAG orchestration | LangChain |
| PDF parsing | PyMuPDF |
| DOCX parsing | python-docx |
| Container | Docker + docker-compose |
| Cloud deploy | Streamlit Cloud (auto from GitHub) |

---

## Repository
github.com/Gyan3233/url-summarizer-ai
