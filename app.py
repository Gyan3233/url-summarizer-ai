import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
import re, time
from urllib.parse import urlparse
from datetime import datetime

st.set_page_config(
    page_title="URL Summarizer & Comparison AI",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background-color: #0f1117; }
.card {
    background: #1e2130; border: 1px solid #2d3147;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 1rem;
}
.card h4 { color: #7c8cf8; margin: 0 0 0.5rem; font-size: 0.93rem; }
.card p  { color: #cdd6f4; line-height: 1.7; margin: 0; font-size: 0.92rem; }
.url-tag {
    display: inline-block; background: #2d3147; color: #89b4fa;
    border-radius: 6px; padding: 2px 10px; font-size: 0.78rem;
    margin-bottom: 0.5rem; font-family: monospace;
}
.badge-ok   { color: #a6e3a1; font-size: 0.78rem; }
.badge-fail { color: #f38ba8; font-size: 0.78rem; }
.compare-box {
    background: #1a1d2e; border: 1px solid #2d3147;
    border-radius: 10px; padding: 1rem 1.2rem; height: 100%;
}
.compare-box h5 { color: #cba6f7; margin: 0 0 0.5rem; font-size: 0.88rem; }
.compare-box p  { color: #a6adc8; line-height: 1.6; margin: 0; font-size: 0.87rem; }
.winner-box {
    background: #1a2a1e; border: 1px solid #3b7a4a;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-top: 1rem;
}
.winner-box h4 { color: #a6e3a1; margin: 0 0 0.5rem; }
.winner-box p  { color: #cdd6f4; line-height: 1.7; margin: 0; font-size: 0.92rem; }
.insight-box {
    background: #1e2130; border-left: 3px solid #7c8cf8;
    border-radius: 0 10px 10px 0; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
}
.insight-box h5 { color: #7c8cf8; margin: 0 0 0.3rem; font-size: 0.88rem; }
.insight-box p  { color: #cdd6f4; line-height: 1.6; margin: 0; font-size: 0.9rem; }
section[data-testid="stSidebar"] { background: #13151f; }
.stButton > button {
    background: linear-gradient(135deg, #7c8cf8, #89b4fa);
    color: #0f1117; border: none; border-radius: 8px;
    font-weight: 600; padding: 0.5rem 1.5rem;
}
.stButton > button:hover { opacity: 0.88; }
.stTextArea textarea {
    background: #1e2130 !important; color: #cdd6f4 !important;
    border: 1px solid #2d3147 !important; border-radius: 8px !important;
}
.stTextInput input {
    background: #1e2130 !important; color: #cdd6f4 !important;
    border: 1px solid #2d3147 !important;
}
[data-testid="stMetricValue"] { color: #cdd6f4 !important; }
[data-testid="stMetricLabel"] { color: #6c7086 !important; }
hr { border-color: #2d3147; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────
for k, v in {"history": [], "api_key": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

def extract_urls(text):
    return list(dict.fromkeys(re.findall(r'https?://[^\s\)\]\>\"\']+', text)))

def scrape(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","footer","header","aside","form"]):
            tag.decompose()
        title = soup.title.string.strip() if soup.title else urlparse(url).netloc
        body = (soup.find("article") or soup.find("main") or
                soup.find("div", {"id":"content"}) or soup.body)
        text = body.get_text(separator="\n", strip=True)[:6000] if body else ""
        return title, text
    except Exception as e:
        return "Error", str(e)

def call_groq(client, prompt, model, max_tokens=500):
    r = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":prompt}],
        max_tokens=max_tokens,
        temperature=0.4,
    )
    return r.choices[0].message.content.strip()

def single_summary(client, title, text, url, style, length, language, model):
    length_map = {"Short (~100 words)":120,"Medium (~250 words)":320,"Long (~500 words)":620}
    style_map = {
        "Concise bullet points":"5-7 clear bullet points, one key idea each.",
        "Detailed paragraphs":"3-4 well-structured paragraphs.",
        "ELI5 (Simple)":"Explain like I am 5 using simple words and short sentences.",
        "Executive brief":"1-sentence TL;DR, 3 key takeaways, 1 recommended action.",
        "Technical deep-dive":"Emphasise methods, data, frameworks, implementation details.",
    }
    prompt = f"""Summarize the webpage below.
Page title: {title}
Source URL: {url}
Style: {style_map.get(style, style)}
Length: approximately {length}. Language: {language}.

--- CONTENT ---
{text}
---
Begin summary directly without repeating the title."""
    return call_groq(client, prompt, model, length_map.get(length, 320))

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Settings")
    st.markdown("---")
    key_input = st.text_input("Groq API Key", type="password",
                               value=st.session_state.api_key, placeholder="gsk_...")
    if key_input:
        st.session_state.api_key = key_input
    st.markdown("[Get free Groq key](https://console.groq.com)")
    st.markdown("---")
    model = st.selectbox("Model", [
        "llama-3.3-70b-versatile","llama3-8b-8192","mixtral-8x7b-32768","gemma2-9b-it"
    ])
    style = st.selectbox("Summary Style", [
        "Concise bullet points","Detailed paragraphs",
        "ELI5 (Simple)","Executive brief","Technical deep-dive"
    ])
    length = st.selectbox("Length", [
        "Short (~100 words)","Medium (~250 words)","Long (~500 words)"
    ], index=1)
    language = st.selectbox("Language", [
        "English","Hindi","Spanish","French","German","Japanese","Chinese (Simplified)","Arabic"
    ])
    timeout = st.slider("Timeout (s)", 5, 30, 12)
    st.markdown("---")
    st.markdown("### History")
    if st.session_state.history:
        for item in reversed(st.session_state.history[-5:]):
            st.markdown(
                f'<div style="background:#1a1d2e;border-left:3px solid #7c8cf8;'
                f'border-radius:0 8px 8px 0;padding:6px 10px;margin-bottom:6px;'
                f'font-size:0.8rem;color:#a6adc8">'
                f'🔗 {item["domain"]}<br>'
                f'<span style="color:#585b70">{item["time"]}</span></div>',
                unsafe_allow_html=True)
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("No history yet.")

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<h1 style='color:#cdd6f4;margin-bottom:0'>URL Summarizer & Comparison AI</h1>
<p style='color:#6c7086;margin-top:4px'>
  Summarize · Compare & rank multiple sources · AI analyst for Power BI dashboard data
</p>""", unsafe_allow_html=True)
st.markdown("---")

mode = st.radio("Mode", [
    "Summarize URLs",
    "Compare & Rank URLs",
    "Power BI AI Analyst"
], horizontal=True, label_visibility="collapsed")
st.markdown("---")

# ══════════════════════════════════════════════════════════════
# MODE 1 — Summarize URLs
# ══════════════════════════════════════════════════════════════
if mode == "Summarize URLs":
    st.markdown("#### Paste one or more URLs")
    col1, col2 = st.columns([3,1])
    with col1:
        prompt = st.text_area("URLs", placeholder=(
            "https://example.com/article\nhttps://another.com/post\n\n"
            "Or: Summarize this for me: https://..."
        ), height=130, label_visibility="collapsed")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("Summarize", use_container_width=True)
        if st.button("Try example", use_container_width=True):
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
        client = Groq(api_key=st.session_state.api_key)
        st.markdown(f"**Found {len(urls)} URL(s)** — processing...")
        st.markdown("---")
        results = []; t0 = time.time()
        for url in urls:
            domain = urlparse(url).netloc
            with st.spinner(f"Processing {domain}..."):
                title, text = scrape(url, timeout)
                if title == "Error":
                    st.markdown(
                        f'<div class="card"><span class="url-tag">{url[:70]}</span>'
                        f'<span class="badge-fail"> Failed</span>'
                        f'<p style="color:#f38ba8">{text}</p></div>',
                        unsafe_allow_html=True)
                    results.append({"url":url,"status":"failed"}); continue
                try:
                    summary = single_summary(client,title,text,url,style,length,language,model)
                    results.append({"url":url,"status":"ok","title":title,
                                    "summary":summary,"domain":domain})
                    st.markdown(
                        f'<div class="card"><span class="url-tag">{domain}</span>'
                        f'<span class="badge-ok" style="margin-left:8px"> Success</span>'
                        f'<h4>{title}</h4>'
                        f'<p>{summary.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)
                    st.session_state.history.append({
                        "domain":domain,"url":url,"title":title,
                        "summary":summary,"time":datetime.now().strftime("%H:%M")
                    })
                except Exception as e:
                    st.markdown(
                        f'<div class="card"><span class="url-tag">{domain}</span>'
                        f'<span class="badge-fail"> LLM error</span>'
                        f'<p style="color:#f38ba8">{e}</p></div>',
                        unsafe_allow_html=True)

        elapsed = round(time.time()-t0, 1)
        ok = sum(1 for r in results if r.get("status")=="ok")
        c1,c2,c3 = st.columns(3)
        c1.metric("Processed", len(urls))
        c2.metric("Successful", ok)
        c3.metric("Time", f"{elapsed}s")
        if ok:
            txt = "\n\n".join(
                f"URL: {r['url']}\nTitle: {r.get('title','')}\n\n{r.get('summary','')}\n{'─'*60}"
                for r in results if r.get("status")=="ok"
            )
            st.download_button("Download summaries (.txt)", txt,
                               f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

# ══════════════════════════════════════════════════════════════
# MODE 2 — Compare & Rank URLs
# ══════════════════════════════════════════════════════════════
elif mode == "Compare & Rank URLs":
    st.markdown("#### Paste 2–5 URLs to compare")
    st.caption("Side-by-side summaries · key differences · ranked recommendation — all in one click")

    col1, col2 = st.columns([3,1])
    with col1:
        raw = st.text_area("URLs to compare", placeholder=(
            "https://techcrunch.com/article-a\n"
            "https://venturebeat.com/article-b\n"
            "https://wired.com/article-c\n\n"
            "Works great for: competing products, news articles, research papers, job postings..."
        ), height=160, label_visibility="collapsed")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        compare_btn = st.button("Compare Now", use_container_width=True)
        if st.button("Try example", use_container_width=True, key="cex"):
            st.session_state["_cex"] = (
                "https://en.wikipedia.org/wiki/OpenAI\n"
                "https://en.wikipedia.org/wiki/Anthropic\n"
                "https://en.wikipedia.org/wiki/Google_DeepMind"
            )
            st.rerun()
    if "_cex" in st.session_state:
        raw = st.session_state.pop("_cex"); compare_btn = True

    if compare_btn and raw.strip():
        if not st.session_state.api_key:
            st.error("Add Groq API key in sidebar."); st.stop()
        urls = extract_urls(raw)
        if len(urls) < 2:
            st.warning("Paste at least 2 URLs to compare."); st.stop()
        if len(urls) > 5:
            urls = urls[:5]; st.info("Using first 5 URLs.")

        client = Groq(api_key=st.session_state.api_key)
        pages = []
        prog = st.progress(0, text="Scraping pages...")
        for i, url in enumerate(urls):
            domain = urlparse(url).netloc
            prog.progress((i+1)/len(urls), text=f"Scraping {domain}...")
            title, text = scrape(url, timeout)
            if title == "Error":
                st.warning(f"Skipping {url}: {text}"); continue
            pages.append({"url":url,"domain":domain,"title":title,"text":text})
        prog.empty()

        if len(pages) < 2:
            st.error("Could not fetch enough pages."); st.stop()

        st.markdown("---")

        # 1. Side-by-side summaries
        st.markdown("### Side-by-side summaries")
        cols = st.columns(len(pages))
        summaries = []
        for col, page in zip(cols, pages):
            with col:
                with st.spinner(f"Summarising {page['domain']}..."):
                    s = single_summary(client, page["title"], page["text"],
                                       page["url"], "Concise bullet points",
                                       "Medium (~250 words)", language, model)
                    summaries.append(s)
                st.markdown(
                    f'<div class="compare-box">'
                    f'<span style="font-size:0.75rem;color:#585b70;font-family:monospace">'
                    f'{page["domain"]}</span>'
                    f'<h5>{page["title"][:55]}{"..." if len(page["title"])>55 else ""}</h5>'
                    f'<p>{s.replace(chr(10),"<br>")}</p></div>',
                    unsafe_allow_html=True)
        st.markdown("---")

        # 2. Key differences
        st.markdown("### Key differences & combined insights")
        with st.spinner("Analysing differences..."):
            sources_block = "\n\n".join(
                f"Source {i+1} — {p['title']} ({p['domain']}):\n{s}"
                for i,(p,s) in enumerate(zip(pages,summaries))
            )
            diff_prompt = f"""You have {len(pages)} source summaries on a related topic.

{sources_block}

Write a combined analysis with these sections:
1. What all sources AGREE on (common ground)
2. KEY DIFFERENCES between sources (facts, perspectives, claims that differ)
3. Unique insights found only in one source
4. Any contradictions or conflicting information

Be specific — reference which source says what. Language: {language}"""
            diff = call_groq(client, diff_prompt, model, 600)

        for line in diff.split("\n"):
            if not line.strip(): continue
            if any(line.startswith(x) for x in ("1.","2.","3.","4.","**","##","#")):
                h = line.replace("**","").replace("#","").lstrip("1234. ").strip()
                st.markdown(f'<div class="insight-box"><h5>{h}</h5></div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-box"><p>{line}</p></div>',
                            unsafe_allow_html=True)
        st.markdown("---")

        # 3. Ranked recommendation
        st.markdown("### Ranked recommendation — which source wins?")
        with st.spinner("Generating ranking..."):
            rank_prompt = f"""Rank these {len(pages)} sources from best to worst.

{sources_block}

Provide:
1. Ranking with scores out of 10 for each source
2. Why the #1 source is the best (depth, accuracy, clarity, unique value)
3. What each source does better or worse
4. Final verdict: which ONE source should someone read if they only have time for one, and why?

Be direct and specific. Language: {language}"""
            ranking = call_groq(client, rank_prompt, model, 500)

        st.markdown(
            f'<div class="winner-box"><h4>Recommendation</h4>'
            f'<p>{ranking.replace(chr(10),"<br>")}</p></div>',
            unsafe_allow_html=True)
        st.markdown("---")

        # Download full report
        report = (
            f"URL COMPARISON REPORT\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Sources: {len(pages)}\n\n{'='*60}\nINDIVIDUAL SUMMARIES\n{'='*60}\n\n"
            + "\n\n".join(
                f"Source {i+1}: {p['title']}\nURL: {p['url']}\n\n{s}\n{'─'*60}"
                for i,(p,s) in enumerate(zip(pages,summaries))
            )
            + f"\n\n{'='*60}\nKEY DIFFERENCES\n{'='*60}\n{diff}"
            + f"\n\n{'='*60}\nRANKED RECOMMENDATION\n{'='*60}\n{ranking}"
        )
        st.download_button("Download full comparison report (.txt)", report,
                           f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

# ══════════════════════════════════════════════════════════════
# MODE 3 — Power BI AI Analyst
# ══════════════════════════════════════════════════════════════
elif mode == "Power BI AI Analyst":
    st.markdown("#### AI Analyst — paste your dashboard data, get business insights")
    st.caption(
        "Paste KPI values, CSV data, or describe your charts. "
        "Ask questions, compare periods, or generate a written report — "
        "this is the AI panel that lives inside your Power BI dashboard."
    )
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Ask anything", "KPI insights", "Period comparison", "Generate report"
    ])

    # Tab 1 — Free-form analyst
    with tab1:
        st.markdown("**Paste your dashboard data and ask any business question**")
        data_input = st.text_area("Your data / question", placeholder=(
            "Revenue Q3: $4.2M (up 12%)\n"
            "Win Rate: 38% (down 2%)\n"
            "Deals Closed: 247, Target: 220\n"
            "Top Region: APAC $1.1M\n\n"
            "Question: Why might win rate have dropped while revenue went up?"
        ), height=200)
        question = st.text_input("Your question",
                                 placeholder="What is driving the revenue increase?")
        if st.button("Analyse", key="a1"):
            if not st.session_state.api_key:
                st.error("Add Groq API key in sidebar."); st.stop()
            if not data_input.strip():
                st.warning("Paste some dashboard data first."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            with st.spinner("Analysing..."):
                p = f"""You are an expert business analyst inside a Power BI dashboard.
Dashboard data: {data_input}
{"Question: " + question if question.strip() else "Provide key insights."}

Respond with:
1. Direct answer (if a question was asked)
2. Top 3 insights from the data
3. Any anomalies or red flags
4. One specific recommended action
Be concise and data-driven. Language: {language}"""
                ans = call_groq(client, p, model, 500)
            st.markdown(f'<div class="card"><h4>Analysis</h4>'
                        f'<p>{ans.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)

    # Tab 2 — KPI insights
    with tab2:
        st.markdown("**Paste your KPIs — get instant insight on each metric**")
        kpi_input = st.text_area("KPI values", placeholder=(
            "Revenue: $4.2M, previous: $3.9M\n"
            "Win Rate: 38%, previous: 40.1%\n"
            "Deals Closed: 247, target: 220\n"
            "Avg Deal Size: $17K, previous: $16.1K\n"
            "Pipeline Coverage: 2.7x, target: 3.0x"
        ), height=180)
        if st.button("Generate KPI insights", key="a2"):
            if not st.session_state.api_key:
                st.error("Add Groq API key in sidebar."); st.stop()
            if not kpi_input.strip():
                st.warning("Paste KPI values first."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            with st.spinner("Analysing KPIs..."):
                p = f"""Analyse these business KPIs:
{kpi_input}
For each KPI give: Status (On track / Watch / Concern), 1-2 sentence insight, one action if needed.
End with an overall dashboard health score 0-10 with brief explanation.
Language: {language}"""
                ins = call_groq(client, p, model, 500)
            st.markdown(f'<div class="card"><h4>KPI Analysis</h4>'
                        f'<p>{ins.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)

    # Tab 3 — Period comparison
    with tab3:
        st.markdown("**Compare two time periods**")
        c1, c2 = st.columns(2)
        with c1:
            pa = st.text_input("Period A label", placeholder="Q2 2025")
            da = st.text_area("Period A data", placeholder=(
                "Revenue: $3.9M\nWin Rate: 40.1%\nDeals: 216\nAvg Deal: $16.1K"
            ), height=150)
        with c2:
            pb = st.text_input("Period B label", placeholder="Q3 2025")
            db = st.text_area("Period B data", placeholder=(
                "Revenue: $4.2M\nWin Rate: 38%\nDeals: 247\nAvg Deal: $17K"
            ), height=150)
        focus = st.text_input("Focus area (optional)",
                              placeholder="Why did win rate drop despite higher revenue?")
        if st.button("Compare periods", key="a3"):
            if not st.session_state.api_key:
                st.error("Add Groq API key in sidebar."); st.stop()
            if not da.strip() or not db.strip():
                st.warning("Fill in both periods."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            with st.spinner("Comparing..."):
                p = f"""Compare these two business periods:
{pa or 'Period A'}: {da}
{pb or 'Period B'}: {db}
{"Focus: " + focus if focus.strip() else ""}
Provide: what improved, what declined, most significant change, unexpected movements,
overall trend direction, top 2 recommended actions.
Language: {language}"""
                comp = call_groq(client, p, model, 600)
            st.markdown(
                f'<div class="card"><h4>Comparison: {pa or "A"} vs {pb or "B"}</h4>'
                f'<p>{comp.replace(chr(10),"<br>")}</p></div>',
                unsafe_allow_html=True)

    # Tab 4 — Generate report
    with tab4:
        st.markdown("**Generate a complete written business report**")
        report_data = st.text_area("Paste all your dashboard data", placeholder=(
            "Dashboard: Sales Performance Q3 2025\n"
            "Revenue: $4.2M | Target: $4.0M | vs Q2: +7.7%\n"
            "Win Rate: 38% | vs Q2: -2.1pp\n"
            "Deals Closed: 247 | Pipeline: $11.4M\n"
            "Top Region: APAC $1.1M | Bottom: LATAM $0.3M\n"
            "Top Product: Insight Engine $1.8M\n"
            "Top Rep: Alice Tan $680K"
        ), height=220)
        c1, c2 = st.columns(2)
        with c1:
            audience = st.selectbox("Audience", [
                "Executive / C-suite","Sales team","Board of directors",
                "Finance team","Operations team"
            ])
        with c2:
            rlen = st.selectbox("Report length", [
                "Brief (1 page)","Standard (2-3 pages)","Detailed (full report)"
            ])
        if st.button("Generate report", key="a4"):
            if not st.session_state.api_key:
                st.error("Add Groq API key in sidebar."); st.stop()
            if not report_data.strip():
                st.warning("Paste dashboard data first."); st.stop()
            client = Groq(api_key=st.session_state.api_key)
            tmap = {"Brief (1 page)":400,"Standard (2-3 pages)":800,"Detailed (full report)":1200}
            with st.spinner("Writing report..."):
                p = f"""Write a professional business report for: {audience}
Length: {rlen}
Data: {report_data}
Structure: Executive Summary, Key Highlights, Areas of Concern,
Regional/Product breakdown, Recommendations (3-5 actions), Outlook.
Tone appropriate for {audience}. Language: {language}"""
                rep = call_groq(client, p, model, tmap.get(rlen,600))
            st.markdown(f'<div class="card"><h4>Business Report</h4>'
                        f'<p>{rep.replace(chr(10),"<br>")}</p></div>',
                        unsafe_allow_html=True)
            st.download_button("Download report (.txt)", rep,
                               f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
