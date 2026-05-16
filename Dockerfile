# ── LENS AI Document Platform — v3.0 ──────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System libraries:
#   libgl1 + libglib2.0-0  → PyMuPDF (PDF rendering)
#   curl                   → healthcheck
# Note: fastembed replaces sentence-transformers
#       so build-essential + CUDA are NOT needed
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app.py .
COPY .streamlit/ .streamlit/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.fileWatcherType=none", \
     "--browser.gatherUsageStats=false"]
