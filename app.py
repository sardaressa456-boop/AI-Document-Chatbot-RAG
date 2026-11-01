"""DocuMind AI — Enterprise-grade RAG Document Assistant with Glassmorphism UI & High-Security Guardrails."""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import streamlit as st
from sentence_transformers import SentenceTransformer

from rag.answering import DEFAULT_MODEL, generate_answer
from rag.documents import MAX_FILES, MAX_TOTAL_PAGES, read_pdf
from rag.retrieval import build_index, search
import database as db
import security

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocuMind AI | Enterprise Document Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com",
        "About": "DocuMind AI — Enterprise RAG document chatbot. Built with Python, Streamlit & Google Gemini.",
    },
)

# ── Global Stylesheet ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
    background: #050b18 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #e2e8f0;
}

/* ── Ambient Radial Glows ── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at 20% 20%, rgba(99,102,241,0.14) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(139,92,246,0.12) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 10%, rgba(16,185,129,0.06) 0%, transparent 60%);
    animation: bgShift 14s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
@keyframes bgShift {
    0%   { transform: translate(0,0) rotate(0deg); }
    100% { transform: translate(2%,2%) rotate(2.5deg); }
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #070d1a 0%, #0c1527 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.22) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1rem; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #fff !important;
    font-weight: 600 !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.25) !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(99,102,241,0.45) !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: rgba(99,102,241,0.06) !important;
    border: 2px dashed rgba(99,102,241,0.35) !important;
    border-radius: 14px !important;
    transition: all 0.25s ease !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
    border-color: rgba(99,102,241,0.85) !important;
    background: rgba(99,102,241,0.12) !important;
}

/* ── Container Layout ── */
.block-container {
    max-width: 1240px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
}

/* ── Header & Branding ── */
.dm-header {
    text-align: center;
    padding: 2rem 1rem 1rem;
    position: relative;
}
.dm-logo-ring {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 76px; height: 76px;
    border-radius: 24px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
    box-shadow: 0 0 35px rgba(99,102,241,0.5), 0 0 70px rgba(99,102,241,0.25);
    font-size: 2.2rem;
    margin: 0 auto 1rem;
    animation: logoGlow 3s ease-in-out infinite alternate;
}
@keyframes logoGlow {
    0%  { box-shadow: 0 0 25px rgba(99,102,241,0.5), 0 0 50px rgba(99,102,241,0.2); }
    100%{ box-shadow: 0 0 45px rgba(139,92,246,0.7), 0 0 90px rgba(139,92,246,0.35); }
}
.dm-title {
    font-size: 3.2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 40%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.4rem;
    line-height: 1.1;
}
.dm-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    font-weight: 400;
    letter-spacing: 0.01em;
}
.dm-badge {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.35);
    color: #a78bfa;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.25rem 0.85rem;
    border-radius: 20px;
    margin-bottom: 0.85rem;
}

/* ── Security Trust Shield ── */
.security-shield {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 30px;
    padding: 0.4rem 1.2rem;
    margin: 1rem auto 1.5rem;
    width: fit-content;
    font-size: 0.82rem;
    color: #34d399;
}
.security-shield span { font-weight: 600; }

/* ── Hero Onboarding Card ── */
.dm-hero {
    background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(139,92,246,0.08) 50%, rgba(16,185,129,0.05) 100%);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 24px;
    padding: 2.2rem 2.5rem;
    margin: 1.5rem 0;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
}
.dm-hero h2 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.4rem;
}
.dm-hero p {
    color: #94a3b8;
    font-size: 0.98rem;
    margin: 0;
    line-height: 1.6;
}
.dm-hero-steps {
    display: flex;
    gap: 1.2rem;
    margin-top: 1.4rem;
    flex-wrap: wrap;
}
.dm-step {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 0.6rem 1.1rem;
    font-size: 0.86rem;
    color: #cbd5e1;
}
.dm-step-num {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff;
    width: 24px; height: 24px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
}

/* ── Source Citation Cards ── */
.source-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(99,102,241,0.22);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    position: relative;
    transition: all 0.25s ease;
}
.source-card:hover {
    border-color: rgba(99,102,241,0.5);
    background: rgba(99,102,241,0.08);
    transform: translateY(-1px);
}
.source-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px; height: 26px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    color: #fff;
    margin-right: 0.5rem;
}
.source-filename {
    font-weight: 600;
    color: #c4b5fd;
    font-size: 0.9rem;
}
.source-page {
    background: rgba(99,102,241,0.16);
    color: #a5b4fc;
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 0.5rem;
}
.source-score {
    position: absolute;
    top: 1rem; right: 1.2rem;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-size: 0.75rem;
    font-weight: 700;
}
.source-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #cbd5e1;
    background: rgba(0,0,0,0.3);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-top: 0.75rem;
    line-height: 1.65;
    border-left: 3px solid rgba(99,102,241,0.5);
}

/* ── Sidebar Brand ── */
.sb-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
}
.sb-brand-icon {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    box-shadow: 0 4px 15px rgba(99,102,241,0.4);
}
.sb-brand-name {
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #f8fafc;
}

/* ── Status Pill ── */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.9rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}
.status-ready {
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.3);
    color: #34d399;
}
.status-waiting {
    background: rgba(245,158,11,0.12);
    border: 1px solid rgba(245,158,11,0.3);
    color: #fbbf24;
}
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 1.6s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.85); }
}

/* ── Streamlit Overrides ── */
.stMetric {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 14px !important;
    padding: 0.9rem 1.1rem !important;
}
.stMetric label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.stMetric [data-testid="stMetricValue"] {
    color: #e0e7ff !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 14px !important;
}
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.025) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 18px !important;
    margin-bottom: 0.85rem !important;
    padding: 1.1rem 1.35rem !important;
}
[data-testid="stChatMessageContent"] p { color: #f1f5f9 !important; font-size: 0.95rem; }
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1.5px solid rgba(99,102,241,0.35) !important;
    border-radius: 16px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: rgba(99,102,241,0.8) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
}

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.35); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.6); }
</style>
""", unsafe_allow_html=True)


# ── Embedding Model Loader ───────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_embedder() -> SentenceTransformer:
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


# ── API Key Provider ─────────────────────────────────────────────────────────
def available_api_key() -> str:
    """Retrieve Gemini API key safely from Streamlit secrets or OS environment."""
    try:
        secret = st.secrets.get("GEMINI_API_KEY", "")
    except (FileNotFoundError, KeyError):
        secret = ""
    return str(secret or os.getenv("GEMINI_API_KEY", ""))


# ── State Initialization ─────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "messages": [],
        "file_signature": None,
        "vector_index": None,
        "stats": {"files": 0, "pages": 0, "chunks": 0},
        "doc_details": [],
        "upload_error": None,
        "db_session_id": None,
        "total_queries": 0,
        "prefilled_query": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Persistent DB session
if st.session_state["db_session_id"] is None:
    st.session_state["db_session_id"] = db.create_session()
    db.log_event("page_view", {"page": "main"}, st.session_state["db_session_id"])


def reset_conversation():
    st.session_state["messages"] = []
    st.session_state["total_queries"] = 0


# ── Maintenance Check ────────────────────────────────────────────────────────
is_maintenance = db.get_setting("maintenance_mode", "false").lower() == "true"
if is_maintenance:
    st.warning("⚠️ **System Maintenance Active:** DocuMind AI is currently undergoing scheduled platform upgrades. Queries are temporarily paused.", icon="🔧")
    st.stop()


# ── Sidebar Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
      <div class="sb-brand-icon">🧠</div>
      <div class="sb-brand-name">DocuMind AI</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Enterprise RAG Document Intelligence")
    st.divider()

    # Document Upload Section
    st.markdown("#### 📁 Document Library")
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help=f"Up to {MAX_FILES} text-based PDFs · Max 15 MB each · {MAX_TOTAL_PAGES} total pages",
    )

    sample_path = Path(__file__).parent / "sample_documents" / "RAG_Quickstart_Guide.pdf"
    if sample_path.exists():
        st.download_button(
            "⬇ Try Sample Document",
            data=sample_path.read_bytes(),
            file_name=sample_path.name,
            mime="application/pdf",
            use_container_width=True,
            help="Download a pre-packaged PDF to test DocuMind instantly",
        )

    # Document Inventory / Details
    if st.session_state.get("doc_details"):
        with st.expander("📄 Indexed Document Manifest", expanded=False):
            for doc in st.session_state["doc_details"]:
                safe_name = security.safe_html(doc['name'])
                st.markdown(f"""
                <div style="font-size:0.8rem;padding:0.4rem 0.6rem;background:rgba(255,255,255,0.03);border-radius:8px;margin-bottom:0.35rem;">
                  <strong style="color:#c4b5fd;">{safe_name}</strong><br>
                  <span style="color:#94a3b8;">{doc['pages']} pgs · {doc['chunks']} chunks · {doc['size_kb']} KB</span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### ⚙️ Intelligence Engine")

    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        DEFAULT_MODEL,
    ]
    model_choice = st.selectbox(
        "Foundation Model",
        MODELS,
        help="gemini-2.5-flash: Ultra-fast & efficient. gemini-2.5-pro: Complex reasoning & deep analysis.",
    )

    key_from_settings = available_api_key()
    api_key = key_from_settings
    if not key_from_settings:
        manual_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIzaSy...",
            help="Your API key stays exclusively in your local session. Never logged or exposed.",
        )
        api_key = manual_key.strip()

    top_k = st.slider("Source Passages (Top-K)", 2, 8, 4, help="Number of semantic passages injected into LLM context")
    temperature = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.1, 0.05, help="0.0 = Strictly factual & grounded, 1.0 = More generative")

    st.divider()

    # RAG Index Status Pill
    index = st.session_state["vector_index"]
    if index is not None:
        st.markdown('<div class="status-pill status-ready"><span class="status-dot"></span> Semantic Index Ready</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill status-waiting"><span class="status-dot"></span> Awaiting Documents</div>', unsafe_allow_html=True)

    st.markdown("")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑 Clear Chat", use_container_width=True):
            reset_conversation()
            st.rerun()
    with col_btn2:
        if st.button("🔄 Reset All", use_container_width=True):
            for key in ["messages", "file_signature", "vector_index", "stats", "doc_details", "upload_error", "total_queries"]:
                st.session_state[key] = {"files": 0, "pages": 0, "chunks": 0} if key == "stats" else ([] if key in ("messages", "doc_details") else (0 if key == "total_queries" else None))
            st.rerun()

    # Export Conversation Feature
    if st.session_state["messages"]:
        st.divider()
        st.markdown("#### 📥 Export Session")
        export_md = "# 🧠 DocuMind AI — Conversation Export\n\n"
        for msg in st.session_state["messages"]:
            export_md += f"### {msg['role'].title()}\n\n{msg['content']}\n\n"
            if msg.get("sources"):
                export_md += "**Sources Cited:**\n"
                for s_item in msg["sources"]:
                    export_md += f"- `{s_item['name']}` (pg. {s_item['page']}, match: {int(s_item['score']*100)}%)\n"
                export_md += "\n"
        st.download_button(
            "⬇ Download Chat (.md)",
            data=export_md,
            file_name=f"documind_chat_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.divider()
    st.caption("🔒 **Security Assured:** PDFs are indexed in-memory. Strict XSS, CSRF, and prompt-injection filters active.")


# ── Main Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="dm-header">
  <div class="dm-logo-ring">🧠</div>
  <div class="dm-badge">✦ Enterprise RAG Architecture · Gemini Powered</div>
  <div class="dm-title">DocuMind AI</div>
  <div class="dm-subtitle">Upload multi-page PDFs · Ask questions in natural language · Receive verified citations</div>
</div>

<div class="security-shield">
  <span>🛡️ Enterprise Security Active</span>
  <span>•</span>
  <span>In-Memory Vector Search</span>
  <span>•</span>
  <span>Zero Cross-Session Retention</span>
  <span>•</span>
  <span>OWASP Guarded</span>
</div>
""", unsafe_allow_html=True)


# ── PDF Processing & Vector Indexing ──────────────────────────────────────────
files = uploaded_files or []
error_message = None

if len(files) > MAX_FILES:
    error_message = f"Maximum {MAX_FILES} PDF files allowed per session."
elif len({f.name for f in files}) != len(files):
    error_message = "Duplicate filenames detected. Please rename files to maintain unique citations."

if error_message:
    st.session_state.update({
        "file_signature": None,
        "vector_index": None,
        "stats": {"files": 0, "pages": 0, "chunks": 0},
        "doc_details": [],
        "upload_error": error_message,
    })
    reset_conversation()

signature = tuple((f.name, hashlib.sha256(f.getvalue()).hexdigest()) for f in files)
if not error_message and signature != st.session_state["file_signature"]:
    st.session_state.update({
        "vector_index": None,
        "stats": {"files": 0, "pages": 0, "chunks": 0},
        "doc_details": [],
        "upload_error": None,
    })
    reset_conversation()

    if files:
        try:
            with st.spinner("⚡ Extracting text, validating documents & constructing semantic index…"):
                chunks, page_count = [], 0
                doc_details = []

                for file in files:
                    file_bytes = file.getvalue()
                    file_chunks, pages = read_pdf(file_bytes, file.name)
                    page_count += pages
                    if page_count > MAX_TOTAL_PAGES:
                        raise ValueError(f"Total page limit ({MAX_TOTAL_PAGES} pages) exceeded across uploaded documents.")
                    chunks.extend(file_chunks)

                    doc_details.append({
                        "name": file.name,
                        "pages": pages,
                        "chunks": len(file_chunks),
                        "size_kb": round(len(file_bytes) / 1024, 1),
                    })

                    db.record_document(
                        st.session_state["db_session_id"],
                        file.name, pages, len(file_chunks), len(file_bytes),
                    )

                if not chunks:
                    raise ValueError("No extractable text found. Scanned or image-only documents require OCR preprocessing.")

                vector_index = build_index(chunks, load_embedder())

                st.session_state.update({
                    "vector_index": vector_index,
                    "stats": {"files": len(files), "pages": page_count, "chunks": len(chunks)},
                    "doc_details": doc_details,
                })

                db.touch_session(
                    st.session_state["db_session_id"],
                    doc_count=len(files), page_count=page_count, chunk_count=len(chunks),
                )
                db.log_event("upload", {"files": [f.name for f in files], "chunks": len(chunks)},
                             st.session_state["db_session_id"])

        except Exception as exc:
            error_message = f"Document processing failed: {exc}"
            st.session_state["upload_error"] = error_message
            db.log_event("error", {"msg": str(exc)}, st.session_state["db_session_id"])

    st.session_state["file_signature"] = signature


# ── Metric KPI Ribbon ─────────────────────────────────────────────────────────
s = st.session_state["stats"]
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("📄 Documents", s["files"])
with m2:
    st.metric("📑 Total Pages", s["pages"])
with m3:
    st.metric("🔍 Indexed Passages", s["chunks"])
with m4:
    st.metric("💬 Queries Handled", st.session_state["total_queries"])

if st.session_state["upload_error"]:
    st.error(st.session_state["upload_error"])


# ── Interactive Workspace & Chat ─────────────────────────────────────────────
index = st.session_state["vector_index"]

if index is None:
    # Onboarding Hero Banner
    st.markdown("""
    <div class="dm-hero">
      <h2>🚀 Get started in 4 simple steps</h2>
      <p>Upload your research papers, company policies, manuals, or legal contracts. DocuMind uses high-dimensional semantic vectors to pinpoint exact answers and cite source pages with complete transparency.</p>
      <div class="dm-hero-steps">
        <div class="dm-step"><span class="dm-step-num">1</span> Upload PDFs in the sidebar</div>
        <div class="dm-step"><span class="dm-step-num">2</span> Enter free Gemini API Key</div>
        <div class="dm-step"><span class="dm-step-num">3</span> Ask in plain English</div>
        <div class="dm-step"><span class="dm-step-num">4</span> Inspect grounded citations</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Starter Topic Recommendations
    st.markdown("##### 💡 Example Document Inquiries:")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.info("📊 **Business & Finance:** Quarterly earnings, compliance statements, revenue growth drivers.")
    with col_t2:
        st.info("🔬 **Technical & Academic:** Architecture decisions, mathematical proofs, experimental results.")

else:
    if not api_key:
        st.warning("⚠️ Enter your **Gemini API Key** in the sidebar to generate synthesized answers. Passages will be retrieved in preview mode.", icon="🔑")

    # Render Prior Messages
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"], avatar="🧑" if message["role"] == "user" else "🧠"):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander(f"📖 {len(message['sources'])} verified citation(s) from documents", expanded=False):
                    for n, src in enumerate(message["sources"], 1):
                        score_pct = int(src['score'] * 100)
                        score_color = "#34d399" if src['score'] > 0.75 else "#fbbf24" if src['score'] > 0.5 else "#f87171"
                        safe_doc_name = security.safe_html(src['name'])
                        safe_snippet = security.safe_html(src['text'][:450])
                        st.markdown(f"""
                        <div class="source-card">
                          <div>
                            <span class="source-num">{n}</span>
                            <span class="source-filename">📄 {safe_doc_name}</span>
                            <span class="source-page">pg. {src['page']}</span>
                            <span class="source-score" style="background:{score_color}22; color:{score_color};">
                              ▲ {score_pct}% Match
                            </span>
                          </div>
                          <div class="source-text">{safe_snippet}{'…' if len(src['text']) > 450 else ''}</div>
                        </div>
                        """, unsafe_allow_html=True)

    # Quick Action Chips for Fast Analysis
    st.markdown("##### ⚡ Quick Analysis Starters:")
    chip_cols = st.columns(5)
    selected_chip = None
    with chip_cols[0]:
        if st.button("📌 Summarize Document", use_container_width=True):
            selected_chip = "Provide a comprehensive executive summary of this document, covering all major themes and conclusions."
    with chip_cols[1]:
        if st.button("📊 Key Data & Numbers", use_container_width=True):
            selected_chip = "Extract all key metrics, statistics, percentages, and financial or quantitative data points found in the document."
    with chip_cols[2]:
        if st.button("🔍 Core Methodology", use_container_width=True):
            selected_chip = "What are the core methodologies, procedures, or architectures detailed in this document?"
    with chip_cols[3]:
        if st.button("⚠️ Risks & Limitations", use_container_width=True):
            selected_chip = "What are the main risks, limitations, potential challenges, or security considerations mentioned?"
    with chip_cols[4]:
        if st.button("🎯 Next Steps & Actions", use_container_width=True):
            selected_chip = "List the key recommendations, action items, and next steps outlined in this document."

    # Chat Input Box
    user_query = st.chat_input("Ask a question about your uploaded documents…", max_chars=2000)
    prompt = selected_chip or user_query

    if prompt:
        # 1. Rate Limiting Check
        allowed, retry_after = security.check_rate_limit(st.session_state["db_session_id"])
        if not allowed:
            st.warning(f"⏳ **Rate limit reached:** Please wait {retry_after} second(s) before sending another query to protect service resources.", icon="⏱️")
            st.stop()

        # 2. Append and render user query
        preceding = list(st.session_state["messages"])
        st.session_state["messages"].append({"role": "user", "content": prompt})
        db.save_message(st.session_state["db_session_id"], "user", prompt)

        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        # 3. Process RAG query
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("🔍 Scanning semantic vector space & formulating grounded answer…"):
                t0 = time.time()
                try:
                    hits = search(index, prompt, load_embedder(), top_k=top_k)
                    sources = [
                        {
                            "name": h.chunk.doc_name,
                            "page": h.chunk.page,
                            "text": h.chunk.text,
                            "score": h.score,
                        }
                        for h in hits
                    ]

                    if not api_key:
                        answer = (
                            "**Semantic Retrieval Preview:** Below are the most relevant excerpts matching your query. "
                            "To get a fully synthesized AI answer, enter your Gemini API key in the sidebar."
                        )
                    else:
                        answer = generate_answer(
                            question=prompt,
                            hits=hits,
                            api_key=api_key,
                            model_name=model_choice,
                            history=preceding[-6:],
                            temperature=temperature,
                        )

                    latency_ms = int((time.time() - t0) * 1000)
                    st.session_state["total_queries"] += 1

                    db.save_message(
                        st.session_state["db_session_id"],
                        "assistant",
                        answer,
                        sources=sources,
                        model=model_choice,
                        latency_ms=latency_ms,
                    )
                    db.log_event("query", {
                        "question": prompt[:200],
                        "model": model_choice,
                        "hits": len(hits),
                        "latency_ms": latency_ms,
                    }, st.session_state["db_session_id"])

                except Exception as exc:
                    answer = f"❌ **Query Execution Error:** {exc}\n\nPlease check your API key, network connectivity, and quota status."
                    sources = []
                    db.log_event("error", {"msg": str(exc)}, st.session_state["db_session_id"])
                    latency_ms = 0

            # Render answer and latency badge
            st.markdown(answer)
            if latency_ms > 0:
                st.caption(f"⚡ Response generated in {latency_ms/1000:.2f}s using `{model_choice}`")

            # Render citation cards
            if sources:
                with st.expander(f"📖 {len(sources)} verified citation(s) from documents", expanded=True):
                    for n, src in enumerate(sources, 1):
                        score_pct = int(src['score'] * 100)
                        score_color = "#34d399" if src['score'] > 0.75 else "#fbbf24" if src['score'] > 0.5 else "#f87171"
                        safe_doc_name = security.safe_html(src['name'])
                        safe_snippet = security.safe_html(src['text'][:450])
                        st.markdown(f"""
                        <div class="source-card">
                          <div>
                            <span class="source-num">{n}</span>
                            <span class="source-filename">📄 {safe_doc_name}</span>
                            <span class="source-page">pg. {src['page']}</span>
                            <span class="source-score" style="background:{score_color}22; color:{score_color};">
                              ▲ {score_pct}% Match
                            </span>
                          </div>
                          <div class="source-text">{safe_snippet}{'…' if len(src['text']) > 450 else ''}</div>
                        </div>
                        """, unsafe_allow_html=True)

        st.session_state["messages"].append({"role": "assistant", "content": answer, "sources": sources})


# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center;padding:1.2rem 0;color:#64748b;font-size:0.84rem;">
  <strong>DocuMind AI</strong> · Enterprise RAG Platform ·
  Powered by <strong style="color:#6366f1">Python</strong> ·
  <strong style="color:#8b5cf6">Streamlit</strong> ·
  <strong style="color:#06b6d4">Sentence Transformers</strong> ·
  <strong style="color:#10b981">Google Gemini</strong> ·
  <a href="/Admin_Panel" target="_self" style="color:#a78bfa;text-decoration:none;font-weight:600;margin-left:0.4rem;">⚙ Admin Control Panel</a>
</div>
""", unsafe_allow_html=True)
