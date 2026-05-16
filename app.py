# ─────────────────────────────────────────────────────────────
#  URL Summarizer & AI Analyst  —  v3.0
#  Modes:
#    1. Summarize URLs
#    2. Compare & Rank  (URLs  OR  uploaded documents)
#    3. Power BI AI Analyst
#    4. Document Chat  (RAG over uploaded PDF / DOCX / TXT)
# ─────────────────────────────────────────────────────────────

import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
import re, time, io, os, tempfile
from urllib.parse import urlparse
from datetime import datetime

# ── Optional heavy imports (graceful fallback if missing) ─────
try:
    import fitz                                    # PyMuPDF
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    from docx import Document as DocxDocument
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

try:
    from fastembed import TextEmbedding
    import faiss, numpy as np
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    RAG_OK = True
except ImportError:
    RAG_OK = False

# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LENS — AI Document Platform",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── LENS AI Document Platform — Design System ── */
/* Base: deep navy-black, teal/cyan accents, amber highlights */
.stApp{background:#060b14}

/* Sidebar */
section[data-testid="stSidebar"]{
  background:#080e1c;
  border-right:1px solid rgba(32,196,203,0.12);
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] p{color:#6b82a8}

/* Inputs */
.stTextArea textarea{
  background:#0d1526!important;color:#c8d8f0!important;
  border:1px solid rgba(32,196,203,0.2)!important;
  border-radius:8px!important;font-size:.92rem!important;
}
.stTextArea textarea:focus{border-color:rgba(32,196,203,0.5)!important;}
.stTextInput input{
  background:#0d1526!important;color:#c8d8f0!important;
  border:1px solid rgba(32,196,203,0.2)!important;border-radius:8px!important;
}
.stTextInput input:focus{border-color:rgba(32,196,203,0.5)!important;}
.stSelectbox>div>div{
  background:#0d1526!important;color:#c8d8f0!important;
  border:1px solid rgba(32,196,203,0.18)!important;
}

/* Buttons */
.stButton>button{
  background:transparent;
  border:1px solid rgba(32,196,203,0.4);
  color:#20c4cb;border-radius:7px;font-weight:500;
  transition:all .2s;letter-spacing:.3px;
}
.stButton>button:hover{
  background:rgba(32,196,203,0.1);
  border-color:#20c4cb;color:#fff;
}
.stButton>button:active{transform:scale(.98)}

/* Metrics */
[data-testid="stMetricValue"]{color:#20c4cb!important;font-size:1.6rem!important}
[data-testid="stMetricLabel"]{color:#4a6080!important;font-size:.78rem!important;letter-spacing:.5px}
[data-testid="stMetric"]{
  background:#0a1220;border:1px solid rgba(32,196,203,0.12);
  border-radius:10px;padding:.8rem 1rem;
}

/* Divider */
hr{border-color:rgba(32,196,203,0.1)}

/* ── Cards ── */
.card{
  background:#0a1220;
  border:1px solid rgba(32,196,203,0.15);
  border-left:3px solid #20c4cb;
  border-radius:10px;
  padding:1.2rem 1.4rem;margin-bottom:1rem;
  position:relative;overflow:hidden;
}
.card::before{
  content:"";position:absolute;top:0;right:0;
  width:120px;height:120px;
  background:radial-gradient(circle at top right,rgba(32,196,203,0.05),transparent 70%);
  pointer-events:none;
}
.card h4{color:#20c4cb;margin:0 0 .5rem;font-size:.93rem;font-weight:500;letter-spacing:.3px}
.card p{color:#a0b4cc;line-height:1.75;margin:0;font-size:.91rem}

/* ── URL tag ── */
.url-tag{
  display:inline-block;background:rgba(32,196,203,0.08);
  color:#20c4cb;border:1px solid rgba(32,196,203,0.2);
  border-radius:5px;padding:2px 10px;font-size:.76rem;
  margin-bottom:.5rem;font-family:monospace;letter-spacing:.2px;
}

/* ── Status badges ── */
.badge-ok{color:#34d399;font-size:.78rem;font-weight:500}
.badge-fail{color:#f87171;font-size:.78rem;font-weight:500}

/* ── Compare boxes ── */
.compare-box{
  background:#080e1c;
  border:1px solid rgba(32,196,203,0.15);
  border-top:2px solid rgba(180,130,255,0.4);
  border-radius:10px;padding:1rem 1.2rem;height:100%;
  position:relative;overflow:hidden;
}
.compare-box::before{
  content:"";position:absolute;top:0;left:0;right:0;height:40px;
  background:linear-gradient(180deg,rgba(180,130,255,0.04),transparent);
  pointer-events:none;
}
.compare-box h5{color:#b482ff;margin:0 0 .5rem;font-size:.88rem;font-weight:500}
.compare-box p{color:#8899b4;line-height:1.65;margin:0;font-size:.87rem}

/* ── Winner box ── */
.winner-box{
  background:#071a10;
  border:1px solid rgba(52,211,153,0.25);
  border-left:3px solid #34d399;
  border-radius:10px;padding:1.2rem 1.4rem;margin-top:1rem;
  position:relative;overflow:hidden;
}
.winner-box::before{
  content:"";position:absolute;top:0;right:0;
  width:100px;height:100px;
  background:radial-gradient(circle at top right,rgba(52,211,153,0.07),transparent 70%);
  pointer-events:none;
}
.winner-box h4{color:#34d399;margin:0 0 .5rem;font-weight:500}
.winner-box p{color:#a0c4b0;line-height:1.7;margin:0;font-size:.92rem}

/* ── Insight box ── */
.insight-box{
  background:#080e1c;
  border-left:3px solid rgba(32,196,203,0.5);
  border-radius:0 8px 8px 0;
  padding:.85rem 1.1rem;margin-bottom:.6rem;
}
.insight-box h5{color:#20c4cb;margin:0 0 .3rem;font-size:.87rem;font-weight:500}
.insight-box p{color:#a0b4cc;line-height:1.65;margin:0;font-size:.89rem}

/* ── RAG Chat ── */
.rag-msg-user{display:flex;justify-content:flex-end;margin-bottom:.7rem}
.rag-msg-user .bubble{
  background:rgba(32,196,203,0.1);color:#c8d8f0;
  border:1px solid rgba(32,196,203,0.2);
  border-radius:12px 2px 12px 12px;
  padding:.65rem 1rem;font-size:.9rem;max-width:80%;line-height:1.65;
}
.rag-msg-ai{display:flex;gap:8px;align-items:flex-start;margin-bottom:.7rem}
.rag-msg-ai .bubble{
  background:#0a1220;color:#a0b4cc;
  border:1px solid rgba(32,196,203,0.15);
  border-radius:2px 12px 12px 12px;
  padding:.65rem 1rem;font-size:.9rem;max-width:88%;line-height:1.65;
}

/* ── Dept cards ── */
.dept-card{
  background:#080e1c;border:1px solid rgba(32,196,203,0.15);
  border-radius:8px;padding:.85rem 1rem;text-align:center;
  cursor:pointer;transition:all .2s;
}
.dept-card:hover{
  border-color:#20c4cb;background:rgba(32,196,203,0.06);
  transform:translateY(-1px);
}
.dept-card h5{color:#20c4cb;margin:0 0 .25rem;font-size:.87rem;font-weight:500}
.dept-card p{color:#6b82a8;margin:0;font-size:.77rem}

/* ── Radio (mode selector) ── */
div[role="radiogroup"]{gap:4px}
div[role="radiogroup"] label{
  background:#0a1220!important;
  border:1px solid rgba(32,196,203,0.15)!important;
  border-radius:7px!important;padding:6px 14px!important;
  color:#6b82a8!important;font-size:.88rem!important;
  transition:all .15s!important;
}
div[role="radiogroup"] label:hover{
  border-color:rgba(32,196,203,0.4)!important;
  color:#20c4cb!important;
}
div[role="radiogroup"] label[data-checked="true"],
div[role="radiogroup"] label[aria-checked="true"]{
  background:rgba(32,196,203,0.1)!important;
  border-color:#20c4cb!important;
  color:#20c4cb!important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{
  background:transparent;border-bottom:1px solid rgba(32,196,203,0.15);gap:0;
}
.stTabs [data-baseweb="tab"]{
  background:transparent;color:#6b82a8;
  border-bottom:2px solid transparent;
  padding:8px 20px;font-size:.88rem;
}
.stTabs [data-baseweb="tab"]:hover{color:#20c4cb}
.stTabs [aria-selected="true"]{
  color:#20c4cb!important;
  border-bottom-color:#20c4cb!important;
  background:transparent!important;
}
.stTabs [data-baseweb="tab-panel"]{padding-top:1.2rem}

/* ── File uploader ── */
[data-testid="stFileUploader"]{
  background:#080e1c;border:1px dashed rgba(32,196,203,0.25);
  border-radius:10px;padding:.5rem;
}

/* ── Progress bar ── */
.stProgress>div>div{background:rgba(32,196,203,0.15)}
.stProgress>div>div>div{background:linear-gradient(90deg,#20c4cb,#34d399)}

/* ── Spinner ── */
.stSpinner>div{border-top-color:#20c4cb!important}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(32,196,203,0.3);border-radius:2px}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────
for k, v in {
    "api_key": "",
    "history": [],
    "rag_index": None,      # FAISS index
    "rag_chunks": [],       # list of text chunks
    "rag_meta": [],         # list of {filename, chunk_id}
    "rag_chat": [],         # [{role, content}]
    "rag_docs_loaded": [],  # filenames successfully indexed
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

DEPT_TEMPLATES = {
    "HR — Resume Comparison": {
        "icon": "👤",
        "desc": "Rank candidates, highlight skill gaps",
        "prompt": (
            "You are an expert HR analyst. Compare these resumes.\n"
            "For each candidate provide:\n"
            "1. Top 3 strengths\n2. Key gaps\n3. Suitability score /10\n"
            "End with a ranked recommendation and the top candidate for the role.\n"
            "Be specific and professional."
        )
    },
    "Legal — Contract Analysis": {
        "icon": "⚖️",
        "desc": "Extract clauses, flag risks",
        "prompt": (
            "You are a senior legal analyst. Analyse this contract.\n"
            "Extract: 1. Key obligations for each party\n"
            "2. Termination clauses\n3. Liability and indemnity provisions\n"
            "4. Risk flags (unusual or missing clauses)\n5. Summary verdict\n"
            "Be precise. Use legal terminology appropriately."
        )
    },
    "Finance — Report Summary": {
        "icon": "💰",
        "desc": "Summarise financials, highlight KPIs",
        "prompt": (
            "You are a financial analyst. Summarise this financial report.\n"
            "Extract: 1. Key financial metrics (revenue, profit, margins)\n"
            "2. Period-over-period changes\n3. Red flags or concerns\n"
            "4. Management commentary highlights\n5. Executive summary\n"
            "Format numbers clearly. Note any missing data."
        )
    },
    "Procurement — Vendor Comparison": {
        "icon": "🏭",
        "desc": "Score vendors, recommend winner",
        "prompt": (
            "You are a procurement specialist. Compare these vendor proposals.\n"
            "Score each vendor on: 1. Pricing (clarity and competitiveness)\n"
            "2. Technical capability\n3. Delivery timeline\n"
            "4. Support and SLA terms\n5. Risk factors\n"
            "Give each a score /10 per category and an overall score.\n"
            "End with a clear recommendation."
        )
    },
    "Sales — RFP Analysis": {
        "icon": "📋",
        "desc": "Extract requirements, draft outline",
        "prompt": (
            "You are a sales engineer. Analyse this RFP.\n"
            "Extract: 1. Core requirements (must-have vs nice-to-have)\n"
            "2. Evaluation criteria and weightings\n"
            "3. Timeline and submission requirements\n"
            "4. Red flags or deal-breakers\n"
            "5. Recommended response outline\n"
            "Be actionable and concise."
        )
    },
    "SAP — Functional Spec": {
        "icon": "⚙️",
        "desc": "Scope, gaps, integration points",
        "prompt": (
            "You are a senior SAP functional consultant. Analyse this specification.\n"
            "Extract: 1. Scope summary (modules, processes covered)\n"
            "2. Key functional requirements\n"
            "3. Integration points and dependencies\n"
            "4. Gaps or ambiguities that need clarification\n"
            "5. Estimated complexity (Low / Medium / High) with justification\n"
            "Use SAP terminology appropriately."
        )
    },
}

# ─────────────────────────────────────────────────────────────
#  UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────
def extract_urls(text):
    return list(dict.fromkeys(re.findall(r'https?://[^\s\)\]\>\"\']+', text)))

def scrape_url(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","footer","header","aside","form"]):
            tag.decompose()
        title = soup.title.string.strip() if soup.title else urlparse(url).netloc
        body  = (soup.find("article") or soup.find("main")
                 or soup.find("div", {"id":"content"}) or soup.body)
        text  = body.get_text(separator="\n", strip=True)[:6000] if body else ""
        return title, text
    except Exception as e:
        return "Error", str(e)

def extract_pdf(file_bytes):
    if not PDF_OK:
        return "PDF support not installed (PyMuPDF missing)"
    try:
        doc  = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text[:50000]
    except Exception as e:
        return f"PDF error: {e}"

def extract_docx(file_bytes):
    if not DOCX_OK:
        return "DOCX support not installed (python-docx missing)"
    try:
        buf  = io.BytesIO(file_bytes)
        doc  = DocxDocument(buf)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text[:50000]
    except Exception as e:
        return f"DOCX error: {e}"

def extract_txt(file_bytes):
    try:
        return file_bytes.decode("utf-8", errors="ignore")[:50000]
    except Exception as e:
        return f"TXT error: {e}"

def extract_file(uploaded_file):
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".pdf"):
        return extract_pdf(data)
    elif name.endswith(".docx"):
        return extract_docx(data)
    elif name.endswith(".txt"):
        return extract_txt(data)
    else:
        return f"Unsupported file type: {uploaded_file.name}"

def call_groq(client, prompt, model, max_tokens=600):
    r = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":prompt}],
        max_tokens=max_tokens,
        temperature=0.4,
    )
    return r.choices[0].message.content.strip()

def single_summary(client, title, text, url, style, length, language, model):
    length_map = {
        "Short (~100 words)": 120,
        "Medium (~250 words)": 320,
        "Long (~500 words)": 620
    }
    style_map = {
        "Concise bullet points": "5-7 clear bullet points, one key idea each.",
        "Detailed paragraphs": "3-4 well-structured paragraphs.",
        "ELI5 (Simple)": "Explain simply — short sentences, everyday words.",
        "Executive brief": "1-sentence TL;DR, 3 key takeaways, 1 recommended action.",
        "Technical deep-dive": "Emphasise methods, data, frameworks, implementation details.",
    }
    prompt = (
        f"Summarize the content below.\n"
        f"Title: {title}\nSource: {url}\n"
        f"Style: {style_map.get(style, style)}\n"
        f"Length: approximately {length}. Language: {language}.\n\n"
        f"--- CONTENT ---\n{text}\n---\n"
        f"Begin summary directly."
    )
    return call_groq(client, prompt, model, length_map.get(length, 320))

# ─────────────────────────────────────────────────────────────
#  RAG FUNCTIONS
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_embedding_model():
    return TextEmbedding("BAAI/bge-small-en-v1.5")

def build_rag_index(texts_and_names: list[tuple[str, str]]):
    """
    texts_and_names: [(text, filename), ...]
    Returns: (faiss_index, all_chunks, all_meta)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " "],
    )
    all_chunks, all_meta = [], []
    for text, fname in texts_and_names:
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_meta.append({"filename": fname, "chunk_id": i})

    model = load_embedding_model()
    embeddings = list(model.embed(all_chunks))
    embeddings = np.array(embeddings, dtype="float32")

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index, all_chunks, all_meta

def rag_retrieve(query, index, chunks, meta, top_k=5):
    model  = load_embedding_model()
    q_vec  = list(model.embed([query]))
    q_vec  = np.array(q_vec, dtype="float32")
    _, I   = index.search(q_vec, top_k)
    results = []
    for idx in I[0]:
        if idx < len(chunks):
            results.append({
                "chunk": chunks[idx],
                "source": meta[idx]["filename"],
                "chunk_id": meta[idx]["chunk_id"]
            })
    return results

def rag_answer(client, query, retrieved, model_name, language):
    context = "\n\n---\n".join(
        f"[Source: {r['source']}]\n{r['chunk']}" for r in retrieved
    )
    prompt = (
        f"You are an AI analyst. Answer the question below ONLY using the provided context.\n"
        f"If the answer is not in the context, say 'I could not find this in the uploaded documents.'\n"
        f"Do not make up information.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n"
        f"Answer in: {language}\n\n"
        f"Provide a clear, well-structured answer with source references where relevant."
    )
    return call_groq(client, prompt, model_name, 600)

# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding:14px 0 10px">
  <div style="font-size:11px;letter-spacing:2px;color:#3a5870;font-weight:400;
              text-transform:uppercase;margin-bottom:10px">Configuration</div>
</div>""", unsafe_allow_html=True)
    key_in = st.text_input("Groq API Key", type="password",
                            value=st.session_state.api_key, placeholder="gsk_...")
    if key_in:
        st.session_state.api_key = key_in
    st.markdown(
        '<a href="https://console.groq.com" style="font-size:11px;color:#20c4cb;'
        'text-decoration:none">Get free key → console.groq.com</a>',
        unsafe_allow_html=True)
    st.markdown('<hr style="border-color:rgba(32,196,203,0.1);margin:12px 0">', unsafe_allow_html=True)

    model = st.selectbox("Model", [
        "llama-3.3-70b-versatile", "llama3-8b-8192",
        "mixtral-8x7b-32768", "gemma2-9b-it"
    ])
    style = st.selectbox("Summary Style", [
        "Concise bullet points", "Detailed paragraphs",
        "ELI5 (Simple)", "Executive brief", "Technical deep-dive"
    ])
    length = st.selectbox("Length", [
        "Short (~100 words)", "Medium (~250 words)", "Long (~500 words)"
    ], index=1)
    language = st.selectbox("Language", [
        "English","Hindi","Spanish","French",
        "German","Japanese","Chinese (Simplified)","Arabic"
    ])
    timeout = st.slider("URL timeout (s)", 5, 30, 12)
    st.markdown("---")

    # RAG status
    if st.session_state.rag_docs_loaded:
        st.markdown("### 📚 Loaded documents")
        for fname in st.session_state.rag_docs_loaded:
            st.markdown(
                f'<div style="background:rgba(52,211,153,0.06);border-left:2px solid #34d399;'
                f'border-radius:0 6px 6px 0;padding:4px 10px;margin-bottom:4px;'
                f'font-size:.79rem;color:#34d399;font-family:monospace">◈ {fname}</div>',
                unsafe_allow_html=True
            )
        if st.button("🗑 Clear documents & chat"):
            for k in ["rag_index","rag_chunks","rag_meta","rag_chat","rag_docs_loaded"]:
                st.session_state[k] = None if k == "rag_index" else []
            st.rerun()
    st.markdown("---")

    if st.session_state.history:
        st.markdown("### 📜 History")
        for item in reversed(st.session_state.history[-5:]):
            st.markdown(
                f'<div style="background:#1a1d2e;border-left:3px solid #7c8cf8;'
                f'border-radius:0 8px 8px 0;padding:6px 10px;margin-bottom:6px;'
                f'font-size:.8rem;color:#a6adc8">🔗 {item["domain"]}<br>'
                f'<span style="color:#585b70">{item["time"]}</span></div>',
                unsafe_allow_html=True
            )
        if st.button("🗑 Clear history"):
            st.session_state.history = []
            st.rerun()

# ─────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────
# ── LENS topbar ──────────────────────────────────────────────
st.markdown("""
<div style="
  background:#080e1c;
  border:1px solid rgba(32,196,203,0.15);
  border-radius:12px;
  padding:14px 22px;
  display:flex;align-items:center;gap:16px;
  margin-bottom:1rem;
  position:relative;overflow:hidden;
">
  <div style="
    position:absolute;top:0;left:0;right:0;bottom:0;
    background:radial-gradient(ellipse at 20% 50%,rgba(32,196,203,0.04),transparent 60%);
    pointer-events:none;
  "></div>

  <!-- Logo -->
  <div style="display:flex;align-items:center;gap:10px;flex-shrink:0">
    <div style="
      width:34px;height:34px;border-radius:8px;
      background:linear-gradient(135deg,#0d7a85,#20c4cb);
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 0 16px rgba(32,196,203,0.25);
    ">
      <span style="color:#fff;font-size:16px;font-weight:700;letter-spacing:-1px">L</span>
    </div>
    <div style="line-height:1.15">
      <div style="font-size:16px;font-weight:500;color:#e0ecf4;letter-spacing:.5px">LENS</div>
      <div style="font-size:8px;letter-spacing:2.5px;color:#3a5870;font-weight:400;text-transform:uppercase">AI Document Platform</div>
    </div>
  </div>

  <!-- Divider -->
  <div style="width:1px;height:28px;background:rgba(32,196,203,0.15);flex-shrink:0"></div>

  <!-- Tagline -->
  <div style="font-size:12px;color:#4a6a80;letter-spacing:.2px">
    Summarize &nbsp;·&nbsp; Compare &nbsp;·&nbsp; Chat &nbsp;·&nbsp; Analyse
  </div>

  <!-- Right pills -->
  <div style="margin-left:auto;display:flex;align-items:center;gap:8px">
    <div style="
      background:rgba(32,196,203,0.08);border:1px solid rgba(32,196,203,0.2);
      border-radius:20px;padding:3px 10px;
      font-size:10px;color:#20c4cb;display:flex;align-items:center;gap:5px;
    ">
      <span style="font-size:8px">⬡</span> Llama 3.3 70B
    </div>
    <div style="
      background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);
      border-radius:20px;padding:3px 10px;
      font-size:10px;color:#34d399;display:flex;align-items:center;gap:5px;
    ">
      <span style="width:5px;height:5px;border-radius:50%;background:#34d399;display:inline-block"></span>
      Live · v3.0
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

mode = st.radio("", [
    "📄  Summarize URLs",
    "⚖️  Compare & Rank",
    "📊  Power BI Analyst",
    "🧠  Document Chat (RAG)",
], horizontal=True, label_visibility="collapsed",
   key="mode_radio")

# Normalise mode key (strip extra spaces for matching)
mode = mode.strip()
st.markdown(
    '<div style="height:2px;background:linear-gradient(90deg,rgba(32,196,203,0.4),rgba(32,196,203,0),rgba(52,211,153,0));'
    'border-radius:2px;margin-bottom:1.2rem"></div>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────
#  MODE 1 — SUMMARIZE URLs
# ─────────────────────────────────────────────────────────────
if "Summarize" in mode:
    st.markdown("#### Paste one or more URLs")
    c1, c2 = st.columns([3,1])
    with c1:
        prompt = st.text_area("URLs", placeholder=(
            "https://example.com/article\nhttps://another.com/post\n\n"
            "Or: Summarize this for me: https://..."
        ), height=130, label_visibility="collapsed")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("⚡ Summarize", use_container_width=True)
        if st.button("📋 Try example", use_container_width=True):
            st.session_state["_ex"] = "https://en.wikipedia.org/wiki/Large_language_model"
            st.rerun()
    if "_ex" in st.session_state:
        prompt = st.session_state.pop("_ex"); run = True

    if run and prompt.strip():
        if not st.session_state.api_key:
            st.error("Add your Groq API key in the sidebar."); st.stop()
        urls = extract_urls(prompt)
        if not urls:
            st.warning("No valid URLs found."); st.stop()
        client  = Groq(api_key=st.session_state.api_key)
        results = []; t0 = time.time()
        st.markdown(f"**Found {len(urls)} URL(s)** — processing...")
        st.markdown("---")
        for url in urls:
            domain = urlparse(url).netloc
            with st.spinner(f"Processing {domain}..."):
                title, text = scrape_url(url, timeout)
                if title == "Error":
                    st.markdown(
                        f'<div class="card"><span class="url-tag">{url[:70]}</span>'
                        f'<span class="badge-fail"> ❌ Failed</span>'
                        f'<p style="color:#f38ba8">{text}</p></div>',
                        unsafe_allow_html=True)
                    results.append({"status":"failed"}); continue
                try:
                    s = single_summary(client, title, text, url, style, length, language, model)
                    results.append({"status":"ok","title":title,"summary":s,"domain":domain})
                    st.markdown(
                        f'<div class="card"><span class="url-tag">{domain}</span>'
                        f'<span class="badge-ok" style="margin-left:8px"> ✅ Done</span>'
                        f'<h4>{title}</h4><p>{s.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)
                    st.session_state.history.append({
                        "domain": domain, "url": url, "title": title,
                        "summary": s, "time": datetime.now().strftime("%H:%M")
                    })
                except Exception as e:
                    st.markdown(
                        f'<div class="card"><span class="url-tag">{domain}</span>'
                        f'<span class="badge-fail"> ❌ LLM error</span>'
                        f'<p style="color:#f38ba8">{e}</p></div>',
                        unsafe_allow_html=True)

        elapsed = round(time.time()-t0, 1)
        ok = sum(1 for r in results if r.get("status")=="ok")
        col1, col2, col3 = st.columns(3)
        col1.metric("Processed", len(urls))
        col2.metric("Successful", ok)
        col3.metric("Time", f"{elapsed}s")
        if ok:
            txt = "\n\n".join(
                f"URL: {r.get('domain','')}\nTitle: {r.get('title','')}\n\n{r.get('summary','')}\n{'─'*60}"
                for r in results if r.get("status")=="ok"
            )
            st.download_button("⬇️ Download summaries (.txt)", txt,
                               f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

# ─────────────────────────────────────────────────────────────
#  MODE 2 — COMPARE & RANK  (URLs or Documents)
# ─────────────────────────────────────────────────────────────
elif "Compare" in mode:
    st.markdown("#### Compare URLs or uploaded documents — side-by-side · differences · ranked winner")

    input_type = st.radio("Input type", ["🔗 URLs", "📁 Upload documents"],
                          horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    pages = []  # list of {title, text, domain/filename}

    if input_type == "🔗 URLs":
        c1, c2 = st.columns([3,1])
        with c1:
            raw = st.text_area("URLs to compare (2–5)", placeholder=(
                "https://techcrunch.com/article-a\n"
                "https://venturebeat.com/article-b\n"
                "https://wired.com/article-c"
            ), height=160, label_visibility="collapsed")
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            go = st.button("⚖️ Compare", use_container_width=True)
            if st.button("📋 Try example", use_container_width=True, key="cex"):
                st.session_state["_cex"] = (
                    "https://en.wikipedia.org/wiki/OpenAI\n"
                    "https://en.wikipedia.org/wiki/Anthropic\n"
                    "https://en.wikipedia.org/wiki/Google_DeepMind"
                )
                st.rerun()
        if "_cex" in st.session_state:
            raw = st.session_state.pop("_cex"); go = True

        if go and raw.strip():
            urls = extract_urls(raw)
            if len(urls) < 2:
                st.warning("Paste at least 2 URLs."); st.stop()
            urls = urls[:5]
            prog = st.progress(0, text="Fetching pages...")
            for i, url in enumerate(urls):
                prog.progress((i+1)/len(urls), text=f"Fetching {urlparse(url).netloc}...")
                title, text = scrape_url(url, timeout)
                if title != "Error":
                    pages.append({"title": title, "text": text,
                                  "label": urlparse(url).netloc})
                else:
                    st.warning(f"Skipped {url}: {text}")
            prog.empty()

    else:  # Upload documents
        # Department template selector
        st.markdown("**Optional: pick an enterprise template**")
        dept_cols = st.columns(3)
        selected_template = st.session_state.get("_dept_template", None)
        for i, (name, info) in enumerate(DEPT_TEMPLATES.items()):
            with dept_cols[i % 3]:
                if st.button(f"{info['icon']} {name.split('—')[0].strip()}",
                             use_container_width=True, key=f"dept_{i}"):
                    st.session_state["_dept_template"] = name
                    st.rerun()
        if selected_template:
            st.success(f"Template active: **{selected_template}** — {DEPT_TEMPLATES[selected_template]['desc']}")
            if st.button("✕ Clear template"):
                del st.session_state["_dept_template"]
                st.rerun()
        st.markdown("---")

        uploaded = st.file_uploader(
            "Upload 2–5 documents (PDF, DOCX, TXT)",
            type=["pdf","docx","txt"],
            accept_multiple_files=True,
            key="compare_upload"
        )
        go = st.button("⚖️ Compare documents", use_container_width=False)

        if go and uploaded:
            if len(uploaded) < 2:
                st.warning("Upload at least 2 documents."); st.stop()
            prog = st.progress(0, text="Extracting text...")
            for i, f in enumerate(uploaded[:5]):
                prog.progress((i+1)/len(uploaded), text=f"Reading {f.name}...")
                text = extract_file(f)
                if not text.startswith("Error") and not text.startswith("PDF error") \
                   and not text.startswith("DOCX error"):
                    pages.append({"title": f.name, "text": text[:6000], "label": f.name})
                else:
                    st.warning(f"Skipped {f.name}: {text[:100]}")
            prog.empty()

    # ── Shared comparison logic ───────────────────────────────
    if pages and len(pages) >= 2:
        if not st.session_state.api_key:
            st.error("Add Groq API key in sidebar."); st.stop()
        client = Groq(api_key=st.session_state.api_key)

        # Use department template prompt if selected
        dept_prompt = None
        if st.session_state.get("_dept_template"):
            dept_prompt = DEPT_TEMPLATES[st.session_state["_dept_template"]]["prompt"]

        # Step 1 — Side-by-side summaries
        st.markdown("---")
        st.markdown("### 📋 Side-by-side summaries")
        cols    = st.columns(len(pages))
        summaries = []
        for col, page in zip(cols, pages):
            with col:
                with st.spinner(f"Summarising {page['label'][:30]}..."):
                    if dept_prompt:
                        s = call_groq(client,
                            f"{dept_prompt}\n\nDocument: {page['title']}\n\n{page['text']}",
                            model, 400)
                    else:
                        s = single_summary(client, page["title"], page["text"],
                                           page["label"], "Concise bullet points",
                                           "Medium (~250 words)", language, model)
                    summaries.append(s)
                st.markdown(
                    f'<div class="compare-box">'
                    f'<span style="font-size:.75rem;color:#585b70;font-family:monospace">'
                    f'{page["label"][:40]}</span>'
                    f'<h5>{page["title"][:55]}{"..." if len(page["title"])>55 else ""}</h5>'
                    f'<p>{s.replace(chr(10),"<br>")}</p></div>',
                    unsafe_allow_html=True)

        # Step 2 — Key differences
        st.markdown("---")
        st.markdown("### 🔍 Key differences & combined insights")
        with st.spinner("Analysing differences..."):
            sources_block = "\n\n".join(
                f"Source {i+1} — {p['title']}:\n{s}"
                for i,(p,s) in enumerate(zip(pages, summaries))
            )
            diff_prompt = (
                f"Analyse {len(pages)} sources on a related topic.\n\n"
                f"{sources_block}\n\n"
                f"Write a combined analysis:\n"
                f"1. What ALL sources AGREE on\n"
                f"2. KEY DIFFERENCES between sources\n"
                f"3. Unique insights found only in one source\n"
                f"4. Any contradictions\n"
                f"Reference which source says what. Language: {language}"
            )
            diff = call_groq(client, diff_prompt, model, 600)

        for line in diff.split("\n"):
            if not line.strip(): continue
            if any(line.startswith(x) for x in ("1.","2.","3.","4.","**","##","#")):
                h = re.sub(r'^[#\*\d\.\s]+','',line).strip()
                st.markdown(f'<div class="insight-box"><h5>{h}</h5></div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-box"><p>{line}</p></div>',
                            unsafe_allow_html=True)

        # Step 3 — Ranked recommendation
        st.markdown("---")
        st.markdown("### 🏆 Ranked recommendation")
        with st.spinner("Generating ranking..."):
            rank_prompt = (
                f"Rank these {len(pages)} sources from best to worst.\n\n"
                f"{sources_block}\n\n"
                f"1. Ranking with scores /10\n"
                f"2. Why #1 wins\n"
                f"3. What each does better/worse\n"
                f"4. Final verdict: which ONE to pick if time-limited and why\n"
                f"Be direct. Language: {language}"
            )
            ranking = call_groq(client, rank_prompt, model, 500)

        st.markdown(
            f'<div class="winner-box"><h4>🏆 Recommendation</h4>'
            f'<p>{ranking.replace(chr(10),"<br>")}</p></div>',
            unsafe_allow_html=True)

        # Download
        st.markdown("---")
        report = (
            f"COMPARISON REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Sources: {len(pages)}\n\n{'='*60}\nINDIVIDUAL SUMMARIES\n{'='*60}\n\n"
            + "\n\n".join(
                f"Source {i+1}: {p['title']}\n\n{s}\n{'─'*60}"
                for i,(p,s) in enumerate(zip(pages, summaries))
            )
            + f"\n\n{'='*60}\nKEY DIFFERENCES\n{'='*60}\n{diff}"
            + f"\n\n{'='*60}\nRANKED RECOMMENDATION\n{'='*60}\n{ranking}"
        )
        st.download_button("⬇️ Download full comparison report (.txt)", report,
                           f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

# ─────────────────────────────────────────────────────────────
#  MODE 3 — POWER BI AI ANALYST
# ─────────────────────────────────────────────────────────────
elif "Power BI" in mode:
    st.markdown("#### Paste dashboard data — get business insights, period comparisons, written reports")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Ask anything", "📈 KPI insights", "🔄 Period comparison", "📝 Generate report"
    ])

    with tab1:
        data_in = st.text_area("Dashboard data / question", placeholder=(
            "Revenue Q3: $4.2M (up 12%)\nWin Rate: 38% (down 2%)\n"
            "Deals: 247, Target: 220\n\nQuestion: Why did win rate drop?"
        ), height=200)
        question = st.text_input("Your question",
                                 placeholder="What is driving the revenue increase?")
        if st.button("🧠 Analyse", key="pbi1"):
            if not st.session_state.api_key: st.error("Add API key."); st.stop()
            if not data_in.strip(): st.warning("Paste data first."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            with st.spinner("Analysing..."):
                pr = (
                    f"You are an expert business analyst in a Power BI dashboard.\n"
                    f"Data: {data_in}\n"
                    f"{'Question: '+question if question.strip() else 'Provide key insights.'}\n\n"
                    f"Respond with: 1. Direct answer  2. Top 3 insights  "
                    f"3. Anomalies or red flags  4. One recommended action\n"
                    f"Language: {language}"
                )
                ans = call_groq(client, pr, model, 500)
            st.markdown(f'<div class="card"><h4>Analysis</h4>'
                        f'<p>{ans.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)

    with tab2:
        kpi_in = st.text_area("KPI values", placeholder=(
            "Revenue: $4.2M, previous: $3.9M\nWin Rate: 38%, previous: 40.1%\n"
            "Deals: 247, target: 220\nAvg Deal: $17K, previous: $16.1K"
        ), height=180)
        if st.button("📈 KPI insights", key="pbi2"):
            if not st.session_state.api_key: st.error("Add API key."); st.stop()
            if not kpi_in.strip(): st.warning("Paste KPIs first."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            with st.spinner("Analysing KPIs..."):
                pr = (
                    f"Analyse these KPIs:\n{kpi_in}\n\n"
                    f"For each: Status (On track / Watch / Concern), "
                    f"1-2 sentence insight, one action if needed.\n"
                    f"End with dashboard health score 0-10.\nLanguage: {language}"
                )
                ins = call_groq(client, pr, model, 500)
            st.markdown(f'<div class="card"><h4>KPI Analysis</h4>'
                        f'<p>{ins.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            pa = st.text_input("Period A label", placeholder="Q2 2025")
            da = st.text_area("Period A data", height=150,
                              placeholder="Revenue: $3.9M\nWin Rate: 40.1%\nDeals: 216")
        with c2:
            pb = st.text_input("Period B label", placeholder="Q3 2025")
            db = st.text_area("Period B data", height=150,
                              placeholder="Revenue: $4.2M\nWin Rate: 38%\nDeals: 247")
        focus = st.text_input("Focus area", placeholder="Why did win rate drop?")
        if st.button("🔄 Compare", key="pbi3"):
            if not st.session_state.api_key: st.error("Add API key."); st.stop()
            if not da.strip() or not db.strip(): st.warning("Fill both periods."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            with st.spinner("Comparing..."):
                pr = (
                    f"Compare these periods:\n{pa or 'A'}: {da}\n{pb or 'B'}: {db}\n"
                    f"{'Focus: '+focus if focus.strip() else ''}\n\n"
                    f"What improved, what declined, most significant change, "
                    f"unexpected movements, overall trend, top 2 recommendations.\n"
                    f"Language: {language}"
                )
                comp = call_groq(client, pr, model, 600)
            st.markdown(
                f'<div class="card"><h4>Comparison: {pa or "A"} vs {pb or "B"}</h4>'
                f'<p>{comp.replace(chr(10),"<br>")}</p></div>',
                unsafe_allow_html=True)

    with tab4:
        rep_data = st.text_area("All dashboard data", height=220, placeholder=(
            "Dashboard: Sales Q3 2025\nRevenue: $4.2M | Target $4.0M | vs Q2: +7.7%\n"
            "Win Rate: 38% | Deals: 247 | Pipeline: $11.4M\nTop Region: APAC $1.1M"
        ))
        c1, c2 = st.columns(2)
        with c1:
            audience = st.selectbox("Audience", [
                "Executive / C-suite","Sales team","Board of directors",
                "Finance team","Operations team"
            ])
        with c2:
            rlen = st.selectbox("Length", [
                "Brief (1 page)","Standard (2-3 pages)","Detailed (full report)"
            ])
        if st.button("📝 Generate report", key="pbi4"):
            if not st.session_state.api_key: st.error("Add API key."); st.stop()
            if not rep_data.strip(): st.warning("Paste data first."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            tmap = {"Brief (1 page)":400,"Standard (2-3 pages)":800,"Detailed (full report)":1200}
            with st.spinner("Writing report..."):
                pr = (
                    f"Write a professional business report for: {audience}\n"
                    f"Length: {rlen}\nData: {rep_data}\n\n"
                    f"Structure: Executive Summary, Key Highlights, Areas of Concern, "
                    f"Regional/Product breakdown, Recommendations (3-5), Outlook.\n"
                    f"Tone appropriate for {audience}. Language: {language}"
                )
                rep = call_groq(client, pr, model, tmap.get(rlen,600))
            st.markdown(f'<div class="card"><h4>Business Report</h4>'
                        f'<p>{rep.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)
            st.download_button("⬇️ Download report (.txt)", rep,
                               f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

# ─────────────────────────────────────────────────────────────
#  MODE 4 — DOCUMENT CHAT (RAG)
# ─────────────────────────────────────────────────────────────
elif "Document Chat" in mode:
    st.markdown("#### Upload documents · then chat with them using AI")
    st.caption(
        "Supports PDF, DOCX, TXT · Multiple documents · "
        "Answers grounded in your documents only · Session-based memory"
    )

    if not RAG_OK:
        st.error(
            "RAG dependencies not installed. Run:\n\n"
            "`pip install sentence-transformers faiss-cpu langchain langchain-community`"
        )
        st.stop()

    # ── Step 1: Upload ────────────────────────────────────────
    st.markdown("### Step 1 — Upload your documents")
    uploaded_files = st.file_uploader(
        "Upload PDF, DOCX, or TXT files",
        type=["pdf","docx","txt"],
        accept_multiple_files=True,
        key="rag_upload"
    )

    col1, col2 = st.columns([2,1])
    with col1:
        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} file(s) selected:**")
            for f in uploaded_files:
                st.markdown(f"• {f.name} ({round(f.size/1024,1)} KB)")
    with col2:
        build_btn = st.button("🔨 Build index & start chat",
                              use_container_width=True,
                              disabled=not bool(uploaded_files))

    if build_btn and uploaded_files:
        if not st.session_state.api_key:
            st.error("Add Groq API key in sidebar."); st.stop()

        with st.spinner("Loading embedding model (first time ~20s, cached after)..."):
            _ = load_embedding_model()

        texts_and_names = []
        errors = []
        prog = st.progress(0, text="Extracting text from documents...")
        for i, f in enumerate(uploaded_files):
            prog.progress((i+1)/len(uploaded_files), text=f"Reading {f.name}...")
            text = extract_file(f)
            if text.startswith("Error") or "error" in text[:20].lower():
                errors.append(f"{f.name}: {text[:100]}")
            else:
                texts_and_names.append((text, f.name))
        prog.empty()

        if errors:
            for e in errors:
                st.warning(f"⚠️ {e}")

        if texts_and_names:
            with st.spinner(f"Building vector index for {len(texts_and_names)} document(s)..."):
                idx, chunks, meta = build_rag_index(texts_and_names)
                st.session_state.rag_index    = idx
                st.session_state.rag_chunks   = chunks
                st.session_state.rag_meta     = meta
                st.session_state.rag_chat     = []
                st.session_state.rag_docs_loaded = [t[1] for t in texts_and_names]

            st.success(
                f"✅ Index built — {len(chunks)} chunks from "
                f"{len(texts_and_names)} document(s). Start chatting below!"
            )
        else:
            st.error("No documents could be parsed. Check file formats.")

    st.markdown("---")

    # ── Step 2: Chat ──────────────────────────────────────────
    if st.session_state.rag_index is not None:
        st.markdown(f"### Step 2 — Chat with your documents")
        loaded = st.session_state.rag_docs_loaded
        st.markdown(
            "Loaded: " + " · ".join(f"`{f}`" for f in loaded),
            unsafe_allow_html=False
        )
        st.markdown("---")

        # Render chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.rag_chat:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="rag-msg-user">'
                        f'<div class="bubble">{msg["content"]}</div></div>',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<div class="rag-msg-ai">'
                        f'<div style="width:28px;height:28px;flex-shrink:0;border-radius:6px;'
                        f'background:#1a2b4a;display:flex;align-items:center;'
                        f'justify-content:center;font-size:14px">🧠</div>'
                        f'<div class="bubble">{msg["content"].replace(chr(10),"<br>")}</div></div>',
                        unsafe_allow_html=True)

        # Suggested questions
        if not st.session_state.rag_chat:
            st.markdown("**Suggested questions:**")
            suggestions = [
                "What are the main topics covered in these documents?",
                "What are the key risks or concerns mentioned?",
                "Summarise the most important findings.",
                "What are the recommendations or next steps?",
                "Are there any contradictions between the documents?",
            ]
            s_cols = st.columns(2)
            for i, sug in enumerate(suggestions[:4]):
                with s_cols[i % 2]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state["_rag_q"] = sug
                        st.rerun()

        # Input
        st.markdown("---")
        c1, c2 = st.columns([5,1])
        with c1:
            user_q = st.text_input(
                "Ask a question about your documents",
                value=st.session_state.pop("_rag_q", ""),
                placeholder="What does the contract say about termination?",
                label_visibility="collapsed",
                key="rag_input"
            )
        with c2:
            ask_btn = st.button("Ask →", use_container_width=True)

        if (ask_btn or user_q) and user_q.strip():
            if not st.session_state.api_key:
                st.error("Add Groq API key in sidebar."); st.stop()

            client = Groq(api_key=st.session_state.api_key)

            with st.spinner("Searching documents and generating answer..."):
                retrieved = rag_retrieve(
                    user_q,
                    st.session_state.rag_index,
                    st.session_state.rag_chunks,
                    st.session_state.rag_meta,
                    top_k=5
                )
                answer = rag_answer(client, user_q, retrieved, model, language)

            # Add to chat
            st.session_state.rag_chat.append({"role":"user",    "content": user_q})
            st.session_state.rag_chat.append({"role":"assistant","content": answer})

            # Show sources used
            unique_sources = list(dict.fromkeys(r["source"] for r in retrieved))
            st.markdown(
                f'<div style="font-size:.78rem;color:#585b70;margin-top:4px">'
                f'Sources used: {" · ".join(unique_sources)}</div>',
                unsafe_allow_html=True)

            st.rerun()

        # Download chat
        if st.session_state.rag_chat:
            chat_txt = "\n\n".join(
                f"{'You' if m['role']=='user' else 'AI'}: {m['content']}"
                for m in st.session_state.rag_chat
            )
            st.download_button(
                "⬇️ Download chat transcript",
                chat_txt,
                f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                key="dl_chat"
            )

    else:
        st.info(
            "Upload your documents above and click **Build index & start chat** to begin.\n\n"
            "**Works best with:** policy documents, contracts, financial reports, "
            "resumes, RFPs, technical specs\n\n"
            "**Supported formats:** PDF · DOCX · TXT"
        )
