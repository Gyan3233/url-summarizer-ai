import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
import re
import time
from urllib.parse import urlparse
from datetime import datetime

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="URL Summarizer AI",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Cards */
    .summary-card {
        background: #1e2130;
        border: 1px solid #2d3147;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .summary-card h4 {
        color: #7c8cf8;
        margin: 0 0 0.4rem 0;
        font-size: 0.95rem;
        word-break: break-all;
    }
    .summary-card p {
        color: #cdd6f4;
        line-height: 1.7;
        margin: 0;
        font-size: 0.93rem;
    }

    /* URL tag */
    .url-tag {
        display: inline-block;
        background: #2d3147;
        color: #89b4fa;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin-bottom: 0.6rem;
        font-family: monospace;
    }

    /* Status badge */
    .badge-ok   { color: #a6e3a1; font-size: 0.78rem; }
    .badge-fail { color: #f38ba8; font-size: 0.78rem; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #13151f; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #7c8cf8, #89b4fa);
        color: #0f1117;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.88; }

    /* Text area */
    .stTextArea textarea {
        background: #1e2130;
        color: #cdd6f4;
        border: 1px solid #2d3147;
        border-radius: 8px;
        font-size: 0.93rem;
    }

    /* Input */
    .stTextInput input {
        background: #1e2130;
        color: #cdd6f4;
        border: 1px solid #2d3147;
        border-radius: 8px;
    }

    /* Metric */
    [data-testid="stMetricValue"] { color: #cdd6f4 !important; }
    [data-testid="stMetricLabel"] { color: #6c7086 !important; }

    /* Divider */
    hr { border-color: #2d3147; }

    /* History items */
    .hist-item {
        background: #1a1d2e;
        border-left: 3px solid #7c8cf8;
        border-radius: 0 8px 8px 0;
        padding: 0.6rem 0.9rem;
        margin-bottom: 0.5rem;
        font-size: 0.82rem;
        color: #a6adc8;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# ── Helpers ───────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def extract_urls(text: str) -> list[str]:
    """Pull all http/https URLs from a block of text."""
    pattern = r'https?://[^\s\)\]\>\"\']+' 
    urls = re.findall(pattern, text)
    # De-duplicate, preserve order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

def scrape_page(url: str, timeout: int = 10) -> tuple[str, str]:
    """
    Fetch a URL and return (title, clean_text).
    Returns ("Error", error_message) on failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer",
                          "header", "aside", "form", "iframe"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else urlparse(url).netloc

        # Prefer article / main content
        content = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"id": "content"})
            or soup.find("div", {"class": re.compile(r"content|article|post|body", re.I)})
            or soup.body
        )
        text = content.get_text(separator="\n", strip=True) if content else ""

        # Trim to 6000 chars to stay within token limits
        if len(text) > 6000:
            text = text[:6000] + "\n[...content trimmed for length...]"

        return title, text

    except requests.exceptions.Timeout:
        return "Error", f"Request timed out after {timeout}s"
    except requests.exceptions.HTTPError as e:
        return "Error", f"HTTP {e.response.status_code}: {e.response.reason}"
    except requests.exceptions.ConnectionError:
        return "Error", "Could not connect — check the URL or your network"
    except Exception as e:
        return "Error", str(e)

def summarize(client: Groq, title: str, text: str, url: str,
              style: str, length: str, language: str, model: str) -> str:
    """Call Groq to summarize the scraped text."""

    style_instructions = {
        "Concise bullet points": "Present the summary as 5-7 clear bullet points. Each bullet should capture one key idea.",
        "Detailed paragraphs":   "Write 3-4 well-structured paragraphs covering the main topics, key facts, and conclusions.",
        "ELI5 (Simple)":         "Explain this like I'm 5 years old. Use very simple words, short sentences, and everyday analogies.",
        "Executive brief":       "Write a crisp executive brief: 1-sentence TL;DR, 3 key takeaways, and 1 recommended action.",
        "Technical deep-dive":   "Provide a technical summary with emphasis on methods, data, frameworks, and implementation details.",
    }

    length_tokens = {"Short (~100 words)": 120, "Medium (~250 words)": 320, "Long (~500 words)": 620}

    prompt = f"""You are an expert content summarizer. Summarize the webpage content below.

Page title : {title}
Source URL : {url}

Style      : {style_instructions.get(style, style)}
Length     : Aim for approximately {length}.
Language   : Respond in {language}.

--- PAGE CONTENT START ---
{text}
--- PAGE CONTENT END ---

Begin the summary directly. Do not repeat the title or URL in your response."""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=length_tokens.get(length, 320),
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        value=st.session_state.api_key,
        placeholder="gsk_...",
        help="Free key at console.groq.com",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.markdown("[Get free Groq API key →](https://console.groq.com)", unsafe_allow_html=True)
    st.markdown("---")

    model = st.selectbox(
        "Model",
        [
            "llama-3.3-70b-versatile",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        index=0,
        help="llama-3.3-70b gives the best summaries",
    )

    style = st.selectbox(
        "Summary Style",
        ["Concise bullet points", "Detailed paragraphs",
         "ELI5 (Simple)", "Executive brief", "Technical deep-dive"],
        index=0,
    )

    length = st.selectbox(
        "Summary Length",
        ["Short (~100 words)", "Medium (~250 words)", "Long (~500 words)"],
        index=1,
    )

    language = st.selectbox(
        "Output Language",
        ["English", "Hindi", "Spanish", "French", "German",
         "Japanese", "Chinese (Simplified)", "Arabic"],
        index=0,
    )

    timeout = st.slider("Request timeout (seconds)", 5, 30, 12)

    st.markdown("---")
    st.markdown("### 📜 History")
    if st.session_state.history:
        for item in reversed(st.session_state.history[-5:]):
            st.markdown(
                f'<div class="hist-item">🔗 {item["domain"]}<br>'
                f'<span style="color:#585b70">{item["time"]}</span></div>',
                unsafe_allow_html=True,
            )
        if st.button("🗑 Clear history"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("No history yet.")

# ── Main UI ───────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#cdd6f4;margin-bottom:0'>🔗 URL Summarizer AI</h1>"
    "<p style='color:#6c7086;margin-top:4px'>Paste one or multiple links — get instant AI summaries</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    user_prompt = st.text_area(
        "Paste your URL(s) here",
        placeholder=(
            "https://en.wikipedia.org/wiki/Artificial_intelligence\n"
            "https://techcrunch.com/some-article\n\n"
            "You can also write: 'Summarize this page for me: https://example.com'"
        ),
        height=140,
        label_visibility="collapsed",
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("⚡ Summarize", use_container_width=True)
    example_btn = st.button("📋 Try example", use_container_width=True)

if example_btn:
    user_prompt = (
        "https://en.wikipedia.org/wiki/Large_language_model\n"
        "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"
    )
    st.session_state["_example_prompt"] = user_prompt
    st.rerun()

if "_example_prompt" in st.session_state:
    user_prompt = st.session_state.pop("_example_prompt")
    run_btn = True

# ── Run ───────────────────────────────────────────────────────
if run_btn and user_prompt.strip():

    if not st.session_state.api_key:
        st.error("⚠️ Please enter your Groq API key in the sidebar. Get one free at console.groq.com")
        st.stop()

    urls = extract_urls(user_prompt)
    if not urls:
        st.warning("No valid URLs found. Make sure your links start with http:// or https://")
        st.stop()

    client = Groq(api_key=st.session_state.api_key)

    st.markdown(f"**Found {len(urls)} URL{'s' if len(urls) > 1 else ''}** — processing...")
    st.markdown("---")

    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
    total_start = time.time()

    results = []

    for idx, url in enumerate(urls):
        domain = urlparse(url).netloc

        with st.spinner(f"Processing {domain}..."):

            # ── Step 1: Scrape ──
            title, page_text = scrape_page(url, timeout=timeout)

            if title == "Error":
                st.markdown(
                    f'<div class="summary-card">'
                    f'<span class="url-tag">{url[:80]}</span><br>'
                    f'<span class="badge-fail">❌ Failed to fetch</span>'
                    f'<p style="color:#f38ba8;margin-top:0.5rem">{page_text}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                results.append({"url": url, "status": "failed", "error": page_text})
                continue

            # ── Step 2: Summarize ──
            try:
                summary = summarize(
                    client, title, page_text, url,
                    style, length, language, model
                )
                results.append({"url": url, "status": "ok",
                                 "title": title, "summary": summary})

                st.markdown(
                    f'<div class="summary-card">'
                    f'<span class="url-tag">{domain}</span>'
                    f'<span class="badge-ok" style="margin-left:8px">✅ Success</span>'
                    f'<h4>{title}</h4>'
                    f'<p>{summary.replace(chr(10), "<br>")}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Save to history
                st.session_state.history.append({
                    "domain": domain,
                    "url": url,
                    "title": title,
                    "summary": summary,
                    "time": datetime.now().strftime("%H:%M"),
                })

            except Exception as e:
                st.markdown(
                    f'<div class="summary-card">'
                    f'<span class="url-tag">{domain}</span>'
                    f'<span class="badge-fail"> ❌ LLM error</span>'
                    f'<p style="color:#f38ba8">{str(e)}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                results.append({"url": url, "status": "llm_error", "error": str(e)})

    # ── Metrics ──
    elapsed = round(time.time() - total_start, 1)
    ok_count = sum(1 for r in results if r["status"] == "ok")

    with metrics_col1:
        st.metric("URLs processed", len(urls))
    with metrics_col2:
        st.metric("Successful", ok_count)
    with metrics_col3:
        st.metric("Time taken", f"{elapsed}s")

    # ── Download all summaries ──
    if ok_count > 0:
        st.markdown("---")
        all_text = "\n\n".join(
            f"URL: {r['url']}\nTitle: {r.get('title','')}\n\n{r.get('summary','')}\n{'─'*60}"
            for r in results if r["status"] == "ok"
        )
        st.download_button(
            label="⬇️ Download all summaries (.txt)",
            data=all_text,
            file_name=f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
        )
