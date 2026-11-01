"""DocuMind AI — Professional Admin Panel (Streamlit multi-page)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import database as db
import security

st.set_page_config(
    page_title="DocuMind Admin | Control Panel",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #04090f !important;
    font-family: 'Inter', sans-serif;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background:
        radial-gradient(ellipse at 15% 30%, rgba(239,68,68,0.08) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 70%, rgba(99,102,241,0.07) 0%, transparent 50%);
    pointer-events: none; z-index: 0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06080f 0%, #0a0f1c 100%) !important;
    border-right: 1px solid rgba(239,68,68,0.15) !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.block-container { max-width: 1300px !important; padding-top: 1.5rem !important; }

/* Admin header */
.admin-header {
    display: flex; align-items: center; gap: 1rem;
    padding: 1.5rem 0 1rem;
    border-bottom: 1px solid rgba(239,68,68,0.15);
    margin-bottom: 1.5rem;
}
.admin-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #ef4444, #dc2626);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem;
    box-shadow: 0 4px 20px rgba(239,68,68,0.35);
}
.admin-title { font-size: 1.8rem; font-weight: 800; color: #f1f5f9; line-height: 1.1; }
.admin-sub { font-size: 0.85rem; color: #64748b; margin-top: 0.15rem; }
.admin-badge {
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.3);
    color: #f87171;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; padding: 0.25rem 0.7rem; border-radius: 20px;
}

/* Stat cards */
.stat-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px; padding: 1.2rem 1.4rem;
    transition: all 0.3s ease; position: relative; overflow: hidden;
}
.stat-card:hover {
    border-color: rgba(99,102,241,0.3);
    background: rgba(99,102,241,0.06);
    transform: translateY(-2px);
}
.stat-card::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 2px; opacity: 0; transition: opacity 0.3s;
}
.stat-card:hover::after { opacity: 1; }
.stat-val { font-size: 2.2rem; font-weight: 800; margin-bottom: 0.2rem; }
.stat-label { font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600; }

/* Section cards */
.section-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px; padding: 1.4rem 1.6rem; margin-bottom: 1rem;
}
.section-title {
    font-size: 1rem; font-weight: 700; color: #e2e8f0;
    margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;
}

/* Table */
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 0.75rem; text-transform: uppercase;
     letter-spacing: 0.08em; color: #64748b; padding: 0.6rem 0.8rem;
     border-bottom: 1px solid rgba(255,255,255,0.07); }
td { padding: 0.65rem 0.8rem; font-size: 0.85rem; color: #cbd5e1;
     border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: top; }
tr:hover td { background: rgba(99,102,241,0.04); }

/* Tags */
.tag {
    display: inline-block; padding: 0.2rem 0.6rem;
    border-radius: 6px; font-size: 0.72rem; font-weight: 600;
}
.tag-green { background: rgba(16,185,129,0.15); color: #34d399; }
.tag-blue  { background: rgba(99,102,241,0.15); color: #818cf8; }
.tag-red   { background: rgba(239,68,68,0.15);  color: #f87171; }
.tag-amber { background: rgba(245,158,11,0.15); color: #fbbf24; }

/* Settings form */
.settings-row {
    display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.75rem;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important; color: #e2e8f0 !important;
}
.stButton button {
    border-radius: 10px !important; font-weight: 600 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(239,68,68,0.3); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Auth guard ─────────────────────────────────────────────────────────────────
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.markdown("""
    <div style="max-width:440px;margin:5rem auto 2rem;background:rgba(255,255,255,0.03);
                border:1px solid rgba(239,68,68,0.3);border-radius:24px;padding:2.5rem;
                box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
      <div style="text-align:center;margin-bottom:1.5rem;">
        <div style="font-size:2.8rem;margin-bottom:0.5rem;">🔐</div>
        <div style="font-size:1.5rem;font-weight:800;color:#f1f5f9;">DocuMind Admin Portal</div>
        <div style="font-size:0.85rem;color:#94a3b8;margin-top:0.3rem;">Secure Infrastructure & Analytics Control</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("admin_login", clear_on_submit=True):
        pwd = st.text_input("Administrator Password", type="password", placeholder="Enter admin password", help="Protected by salted cryptographic verification and brute-force lockout.")
        submitted = st.form_submit_button("🔓 Authenticate & Access", use_container_width=True)
        if submitted:
            success, msg = security.verify_admin_password(pwd, st.session_state)
            if success:
                st.session_state["admin_authenticated"] = True
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    st.stop()


# ── Admin header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="admin-header">
  <div class="admin-icon">⚙️</div>
  <div>
    <div class="admin-title">DocuMind Admin</div>
    <div class="admin-sub">Platform Control Panel · Real-time Analytics · System Configuration</div>
  </div>
  <div style="margin-left:auto"><span class="admin-badge">🔴 Live</span></div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Admin Navigation")
    page = st.radio(
        "Go to",
        ["📊 Dashboard", "💬 Sessions & Chats", "📄 Documents", "📈 Analytics", "⚙️ Settings", "🧪 System"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["admin_authenticated"] = False
        st.rerun()
    st.caption("DocuMind Admin Panel v2.0")
    st.caption("⚡ Powered by SQLite + Streamlit")


# ── Get live data ──────────────────────────────────────────────────────────────
summary = db.get_analytics_summary()
settings = db.get_all_settings()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🗂 Total Sessions", summary["total_sessions"])
    with col2:
        st.metric("💬 Total Queries", summary["user_queries"])
    with col3:
        st.metric("📄 Documents Uploaded", summary["total_docs"])
    with col4:
        st.metric("⚡ Avg Latency", f"{summary['avg_latency_ms']} ms")

    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("📈 Daily Queries (Last 30 days)")
        daily = summary.get("daily_queries", [])
        if daily:
            import pandas as pd
            df = pd.DataFrame(daily)
            df.columns = ["Date", "Queries"]
            df = df.sort_values("Date")
            st.bar_chart(df.set_index("Date"), color="#6366f1", use_container_width=True)
        else:
            st.info("No query data yet. Start chatting to see analytics!")

    with col6:
        st.subheader("🤖 Model Usage")
        top_models = summary.get("top_models", [])
        if top_models:
            for m in top_models:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:0.6rem 0.8rem;background:rgba(99,102,241,0.08);
                            border:1px solid rgba(99,102,241,0.15);border-radius:10px;margin-bottom:0.5rem;">
                  <span style="font-size:0.85rem;color:#a78bfa;font-weight:600;">{m['model'] or 'unknown'}</span>
                  <span style="background:rgba(99,102,241,0.2);color:#818cf8;border-radius:6px;
                               padding:0.15rem 0.55rem;font-size:0.75rem;font-weight:700;">{m['cnt']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No model data yet.")

    # Error summary
    col7, col8 = st.columns(2)
    with col7:
        st.subheader("⚠️ Errors")
        st.metric("Total Errors Logged", summary["errors"],
                  delta=None if summary["errors"] == 0 else f"{summary['errors']} issues",
                  delta_color="inverse")
    with col8:
        st.subheader("💡 Quick Stats")
        st.markdown(f"""
        <div class="section-card">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
            <div><div style="font-size:1.4rem;font-weight:800;color:#f1f5f9;">{summary['total_messages']}</div>
                 <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Total Messages</div></div>
            <div><div style="font-size:1.4rem;font-weight:800;color:#34d399;">{summary['total_sessions']}</div>
                 <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Active Sessions</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Sessions & Chats
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬 Sessions & Chats":
    st.subheader("💬 User Sessions")

    sessions = db.list_sessions(limit=50)
    if not sessions:
        st.info("No sessions recorded yet.")
    else:
        # Search/filter
        search_q = st.text_input("🔍 Filter sessions", placeholder="Search by session ID or model…")
        if search_q:
            sessions = [s for s in sessions if
                        search_q.lower() in s.get("session_id","").lower() or
                        search_q.lower() in (s.get("model_used") or "").lower()]

        st.caption(f"Showing {len(sessions)} session(s)")

        for sess in sessions:
            with st.expander(f"🗂 Session {sess['session_id'][:12]}… · {sess['last_active'][:19]} · {sess['message_count']} messages"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Messages", sess["message_count"])
                c2.metric("Docs", sess["doc_count"])
                c3.metric("Pages", sess["page_count"])
                c4.metric("Chunks", sess["chunk_count"])
                st.caption(f"Model: {sess.get('model_used','—')} · Created: {sess['created_at'][:19]}")

                if st.button("📜 View Chat History", key=f"chat_{sess['session_id']}"):
                    msgs = db.get_messages(sess["session_id"])
                    for m in msgs:
                        role_icon = "🧑" if m["role"] == "user" else "🧠"
                        role_color = "#6366f1" if m["role"] == "user" else "#10b981"
                        safe_content = security.safe_html(m['content'][:500]) + ("…" if len(m['content']) > 500 else "")
                        safe_role = security.safe_html(m['role'].title())
                        safe_time = security.safe_html(m['created_at'][:19])
                        latency_str = f"· ⚡ {int(m['latency_ms'])}ms" if m.get('latency_ms') else ""
                        st.markdown(f"""
                        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
                                    border-radius:12px;padding:0.75rem 1rem;margin-bottom:0.5rem;
                                    border-left:3px solid {role_color};">
                          <div style="font-size:0.75rem;color:#64748b;margin-bottom:0.3rem;">
                            {role_icon} {safe_role} · {safe_time} {latency_str}
                          </div>
                          <div style="color:#e2e8f0;font-size:0.88rem;">{safe_content}</div>
                        </div>
                        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Documents
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄 Documents":
    st.subheader("📄 Uploaded Documents")
    docs = db.list_documents(limit=200)
    if not docs:
        st.info("No documents have been uploaded yet.")
    else:
        st.caption(f"{len(docs)} document(s) recorded across all sessions")
        import pandas as pd
        df = pd.DataFrame(docs)[["filename", "pages", "chunks", "size_bytes", "uploaded_at", "session_id"]]
        df["size_kb"] = (df["size_bytes"] / 1024).round(1)
        df["session"] = df["session_id"].str[:8] + "…"
        df["uploaded_at"] = df["uploaded_at"].str[:19]
        display_df = df[["filename", "pages", "chunks", "size_kb", "uploaded_at", "session"]].copy()
        display_df.columns = ["Filename", "Pages", "Chunks", "Size (KB)", "Uploaded At", "Session"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Summary charts
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Pages per Document")
            st.bar_chart(df.set_index("filename")["pages"], color="#6366f1", use_container_width=True)
        with col2:
            st.subheader("Chunks per Document")
            st.bar_chart(df.set_index("filename")["chunks"], color="#8b5cf6", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Analytics
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Analytics":
    st.subheader("📈 Platform Analytics")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sessions",  summary["total_sessions"])
    col2.metric("Total Queries",   summary["user_queries"])
    col3.metric("Avg Latency (ms)",summary["avg_latency_ms"])

    st.divider()
    st.subheader("📅 Query Volume — Last 30 Days")
    daily = summary.get("daily_queries", [])
    if daily:
        import pandas as pd
        df = pd.DataFrame(daily)
        df.columns = ["Date", "Queries"]
        df = df.sort_values("Date")
        st.area_chart(df.set_index("Date"), color="#6366f1", use_container_width=True)
    else:
        st.info("No data yet.")

    st.subheader("🤖 Queries by Model")
    top_models = summary.get("top_models", [])
    if top_models:
        import pandas as pd
        mdf = pd.DataFrame(top_models)
        mdf.columns = ["Model", "Queries"]
        st.bar_chart(mdf.set_index("Model"), color="#8b5cf6", use_container_width=True)

    st.subheader("🚨 Error Log Summary")
    st.metric("Total Errors", summary["errors"])
    if summary["errors"] > 0:
        st.warning("Check application logs for error details.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Settings
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.subheader("⚙️ Platform Settings")
    st.caption("Changes are saved immediately to the database and take effect on next session.")

    with st.form("settings_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### 📁 Document Limits")
            max_files = st.number_input("Max files per session", 1, 20,
                                        int(settings.get("max_files", 5)))
            max_pages = st.number_input("Max total pages", 10, 2000,
                                        int(settings.get("max_total_pages", 200)))
            max_mb = st.number_input("Max upload size (MB)", 1, 100,
                                     int(settings.get("max_upload_size_mb", 15)))

        with col2:
            st.markdown("##### 🤖 AI Defaults")
            default_model = st.selectbox("Default model",
                                         ["gemini-2.5-flash","gemini-2.5-pro","gemini-2.0-flash","gemini-2.5-flash-lite"],
                                         index=0)
            top_k = st.number_input("Default top-k passages", 1, 10,
                                    int(settings.get("top_k_default", 4)))
            rate_limit = st.number_input("Rate limit (queries/hour)", 1, 1000,
                                         int(settings.get("rate_limit_queries_per_hour", 60)))

        st.markdown("##### 🌐 UI Settings")
        welcome_msg = st.text_area("Welcome message",
                                   value=settings.get("welcome_message", ""),
                                   height=80)
        maintenance = st.checkbox("🔧 Maintenance mode (blocks all users)",
                                  value=settings.get("maintenance_mode","false") == "true")

        submitted = st.form_submit_button("💾 Save All Settings", use_container_width=True)
        if submitted:
            db.set_setting("max_files", str(max_files))
            db.set_setting("max_total_pages", str(max_pages))
            db.set_setting("max_upload_size_mb", str(max_mb))
            db.set_setting("default_model", default_model)
            db.set_setting("top_k_default", str(top_k))
            db.set_setting("rate_limit_queries_per_hour", str(rate_limit))
            db.set_setting("welcome_message", welcome_msg)
            db.set_setting("maintenance_mode", "true" if maintenance else "false")
            st.success("✅ Settings saved successfully!")
            st.rerun()

    # Show raw settings
    with st.expander("🔍 Raw Settings Store"):
        all_s = db.get_all_settings()
        for k, v in all_s.items():
            st.markdown(f"`{k}` = **{v}**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: System
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧪 System":
    st.subheader("🧪 System Health & Info")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🗄 Database Status")
        from pathlib import Path
        db_path = Path(__file__).parent.parent / "data" / "documind.db"
        if db_path.exists():
            size_kb = db_path.stat().st_size / 1024
            st.success(f"✅ Database online — {size_kb:.1f} KB")
        else:
            st.error("❌ Database file not found")

        st.markdown("#### 📦 Installed Packages")
        import importlib
        packages = ["streamlit", "sentence_transformers", "fitz", "numpy", "google.genai"]
        for pkg in packages:
            try:
                mod = importlib.import_module(pkg)
                ver = getattr(mod, "__version__", "✓")
                st.markdown(f"<span style='color:#34d399'>✅</span> `{pkg}` — {ver}", unsafe_allow_html=True)
            except ImportError:
                st.markdown(f"<span style='color:#f87171'>❌</span> `{pkg}` — not installed", unsafe_allow_html=True)

    with col2:
        st.markdown("#### ⚙️ Runtime Info")
        import sys, platform
        st.markdown(f"- **Python:** {sys.version.split()[0]}")
        st.markdown(f"- **Platform:** {platform.system()} {platform.release()}")
        st.markdown(f"- **Architecture:** {platform.machine()}")

        st.markdown("#### 🗂 Data Directory")
        data_dir = Path(__file__).parent.parent / "data"
        if data_dir.exists():
            files = list(data_dir.iterdir())
            st.markdown(f"📁 `data/` — {len(files)} file(s)")
            for f in files:
                st.markdown(f"  - `{f.name}` ({f.stat().st_size/1024:.1f} KB)")
        else:
            st.info("Data directory will be created on first use.")

    st.divider()
    st.markdown("#### 🗑 Danger Zone")
    st.error("⚠️ These actions are irreversible!")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑 Clear All Analytics Events", use_container_width=True):
            db.clear_analytics()
            st.success("✅ Analytics events cleared successfully.")
            st.rerun()
    with c2:
        if st.button("🔄 Reset Admin Settings to Defaults", use_container_width=True):
            db.reset_settings()
            st.success("✅ Settings reset to default values.")
            st.rerun()
