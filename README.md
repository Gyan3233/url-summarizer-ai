# 🔗 URL Summarizer AI

Paste any URL → get an instant AI summary. Runs on Docker Desktop.

## Folder structure

```
url_summarizer/
├── app.py                ← Streamlit app
├── Dockerfile            ← Container definition
├── docker-compose.yml    ← Run with one command
├── requirements.txt      ← Python packages
├── .env.example          ← Key template
├── .gitignore
└── .streamlit/
    └── config.toml       ← Dark theme
```

---

## Run it (3 steps)

### Step 1 — Get your free Groq API key
Go to → https://console.groq.com
Sign up → API Keys → Create Key
Looks like: `gsk_xxxxxxxxxxxxxxxx`

### Step 2 — Create your .env file
In the project folder, create a file called `.env`:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

### Step 3 — Start the app
```bash
docker-compose up --build
```

Open browser → http://localhost:8501

---

## Stop the app
```bash
docker-compose down
```

## Restart after editing app.py
```bash
docker-compose up --build
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 8501 already in use | Change `"8501:8501"` to `"8502:8501"` in docker-compose.yml |
| API key error | Check .env has no quotes: `GROQ_API_KEY=gsk_abc...` not `GROQ_API_KEY="gsk_abc..."` |
| Container won't start | Make sure Docker Desktop is running before `docker-compose up` |
| URL fetch fails | Some sites block scrapers — try a Wikipedia link to test |
