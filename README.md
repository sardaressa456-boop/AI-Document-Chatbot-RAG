# 🧠 DocuMind AI — Enterprise-Grade RAG Document Assistant

<div align="center">

![DocuMind AI](https://img.shields.io/badge/DocuMind-AI%20Chatbot-6366f1?style=for-the-badge&logo=streamlit)
![Security Hardened](https://img.shields.io/badge/Security-Enterprise%20Hardened-10b981?style=for-the-badge&logo=shield)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45+-ff4b4b?style=for-the-badge&logo=streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285f4?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10b981?style=for-the-badge)

**A production-ready, security-hardened AI document intelligence platform with local semantic search, grounded source citations, conversation history, analytics telemetry, and a multi-page administrative control panel.**

[🚀 Deploy Live to Web](#-deploy-live-to-public-web-google-chrome) · [🛡️ Security Architecture](#-security--hardening-defense-in-depth) · [📖 Architecture](#-architecture) · [⚙️ Admin Panel](#-admin-panel)

</div>

---

## ✨ Features & Capabilities

| Module | Features |
|---|---|
| 📄 **Document Processing** | Upload 1–5 text PDFs (up to 15 MB each, 200 total pages). Automatic magic-byte inspection (`%PDF-`), filename sanitization, and path-traversal prevention. |
| 🧠 **Local Semantic RAG** | In-memory `sentence-transformers` embeddings (`all-MiniLM-L6-v2`) with normalized cosine similarity search — zero external vector database required. |
| 🛡️ **Defense-in-Depth Security** | Rate limiting (sliding window), prompt injection detection, safe HTML escaping (XSS immune), salted constant-time admin authentication with 15-minute brute-force lockout. |
| 📖 **Verified Citations** | Every answer cites exact document name, page number, match percentage, and preview excerpt inside interactive cards. |
| 💬 **Session Intelligence** | Interactive Quick Analysis Starters, rolling conversation history, chat export to Markdown (`.md`), and in-memory session isolation. |
| 📊 **Admin & Telemetry** | Multi-page Streamlit admin suite with real-time KPI metrics, query volume charts, session inspector, system health monitors, and configurable limits. |
| 🎨 **Executive UI / UX** | Glassmorphism 2.0 design with subtle glowing radial gradients, dark mode, Inter & JetBrains Mono typography, and responsive controls. |
| 🤖 **Multi-Model Support** | Hot-switch between `gemini-2.5-flash`, `gemini-2.5-pro`, and `gemini-2.0-flash`. |

---

## 🛡️ Security & Hardening (Defense in Depth)

DocuMind AI is architected from the ground up to prevent malicious attacks in public web deployments:

```
                  ┌────────────────────────────────────────┐
                  │          USER QUERY / UPLOAD           │
                  └──────────────────┬─────────────────────┘
                                     │
                 ┌───────────────────▼─────────────────────┐
                 │  LAYER 1: Rate Limiter (Sliding Window) │ ➔ Blocks DoS / Quota Draining
                 └───────────────────┬─────────────────────┘
                                     │
                 ┌───────────────────▼─────────────────────┐
                 │  LAYER 2: Input Sanitization & Magic B. │ ➔ Blocks PDF Bombs & Path Traversal
                 └───────────────────┬─────────────────────┘
                                     │
                 ┌───────────────────▼─────────────────────┐
                 │  LAYER 3: Prompt Injection Guardrails   │ ➔ Blocks Jailbreaks & System Overrides
                 └───────────────────┬─────────────────────┘
                                     │
                 ┌───────────────────▼─────────────────────┐
                 │  LAYER 4: Strict XML Chunk Isolation    │ ➔ Treats document text as untrusted data
                 └───────────────────┬─────────────────────┘
                                     │
                 ┌───────────────────▼─────────────────────┐
                 │  LAYER 5: XSS HTML Escaping Engine      │ ➔ 100% immune to Stored & Reflected XSS
                 └───────────────────┬─────────────────────┘
                                     │
                                     ▼
                        [ SAFE GROUNDED RESPONSE ]
```

1. **Stored & Reflected XSS Prevention (`security.safe_html`)**:
   - All dynamic strings, document titles, user questions, and retrieved excerpts are strictly escaped before rendering in any HTML blocks.
2. **Denial-of-Service & Quota Exhaustion Defense (`security.RateLimiter`)**:
   - Sliding-window rate limiting prevents automated scraping or API bill draining.
3. **Adversarial Prompt Injection Defense (`security.detect_prompt_injection`)**:
   - Real-time pattern matching detects attempts to bypass system instructions ("ignore previous instructions", "DAN mode", "reveal system prompt").
   - Retrieved excerpts are strictly wrapped in `<document_chunk>` XML blocks with system prompts instructing the LLM to treat them purely as untrusted passive data.
4. **Path Traversal & PDF Bomb Defense (`security.validate_pdf_bytes`)**:
   - Validates file magic bytes (`%PDF-`), blocks executable extensions, limits memory allocation, and sanitizes filenames against directory traversal (`../`).
5. **Cryptographic Admin Protection (`security.verify_admin_password`)**:
   - Salted SHA-256 verification using `hmac.compare_digest` to eliminate timing attacks.
   - Enforces a 15-minute lockout after 5 consecutive failed attempts.
6. **Zero Cross-Session Data Leakage**:
   - Vector indices and embeddings reside in memory per browser session (`st.session_state`). Concurrent visitors cannot see or access each other's documents.

---

## 🏗 Architecture

```
AI-Document-Chatbot-RAG/
├── app.py                   ← Executive Streamlit application & chat interface
├── database.py              ← SQLite persistence layer (sessions, messages, analytics)
├── security.py              ← Defense-in-depth security engine (Rate limits, XSS, Auth, Sanitation)
├── pages/
│   └── 1_Admin_Panel.py     ← Multi-page administrative monitoring & control suite
├── rag/
│   ├── documents.py         ← PDF validation, text extraction & overlapping chunking
│   ├── retrieval.py         ← Local semantic embedding index & vector similarity search
│   └── answering.py         ← Gemini prompt construction & citation grounding
├── sample_documents/
│   └── RAG_Quickstart_Guide.pdf  ← Instant test document
├── tests/
│   ├── test_documents.py    ← PDF parsing & chunking tests
│   ├── test_retrieval.py    ← Semantic search & prompt tests
│   └── test_security.py     ← Security, XSS, rate-limit & injection tests
├── .streamlit/
│   ├── config.toml          ← Production server config & theme
│   └── secrets.toml.example ← Secrets template
├── Dockerfile               ← Production multi-stage Docker build
├── Procfile                 ← Web server entrypoint
├── requirements.txt         ← Production Python dependencies
└── requirements-dev.txt     ← Developer tools
```

---

## 🚀 Deploy Live to Public Web (Google Chrome)

You can deploy DocuMind AI to the public web so **anyone around the world can open it in Google Chrome** with a secure `https://` domain in less than 3 minutes using **Streamlit Community Cloud** (100% Free & Perpetual):

### Method 1: Streamlit Community Cloud (Recommended — 100% Free)

1. **Push this repository to your GitHub account** (see [GitHub Setup](#-push-to-your-github-account) below).
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
3. Click **"New app"**.
4. Select:
   - **Repository:** `your-username/AI-Document-Chatbot-RAG`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Advanced settings"** and add your secrets:
   ```toml
   GEMINI_API_KEY = "your-actual-gemini-api-key"
   ADMIN_PASSWORD = "your-strong-custom-password"
   ```
6. Click **"Deploy"**!
7. Within 60 seconds, your application is live on a public URL like:
   `https://documind-ai.streamlit.app`
   *(Anyone on Google Chrome, Safari, Firefox, or mobile can access it securely!)*

> [!TIP]
> **Custom Domain**: You can attach your own custom domain (e.g., `https://chat.yourcompany.com`) directly via Streamlit Cloud settings or Cloudflare!

---

### Method 2: Docker / Cloud Run / Render / Railway

You can deploy anywhere using the included production `Dockerfile`:

```bash
# 1. Build the container image
docker build -t documind-ai .

# 2. Run container
docker run -p 8501:8501 -e GEMINI_API_KEY="your-key" documind-ai
```

---

## 🐙 Push to Your GitHub Account

Run these commands in your terminal to publish this project to your GitHub:

```bash
# 1. Check git status
git status

# 2. Add all project files
git add .

# 3. Create initial commit
git commit -m "feat: DocuMind AI - High-Security RAG Document Assistant with Glassmorphism UI"

# 4. Create a new repository on https://github.com/new (e.g., named 'AI-Document-Chatbot-RAG')

# 5. Link your local repo to GitHub (replace with your GitHub username)
git remote add origin https://github.com/<your-username>/AI-Document-Chatbot-RAG.git

# 6. Push to GitHub
git branch -M main
git push -u origin main
```

---

## 💻 Local Quickstart

### Prerequisites
- Python 3.11 or higher
- Google Gemini API key ([Get a free key here](https://aistudio.google.com/app/apikey))

### 1. Setup Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
```bash
# Copy example environment configuration
cp .env.example .env

# Edit .env and paste your GEMINI_API_KEY
```

### 4. Run Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Security & Regression Tests

Run the full automated test suite (all 14 tests):

```bash
python -m unittest discover -s tests -v
```

All tests pass offline with zero external network dependencies.

---

## ⚙️ Admin Panel

Access the administrative monitoring portal at `http://localhost:8501/Admin_Panel`:
- **Default Password:** `documind2025` *(Change via `ADMIN_PASSWORD` in `.env` or Streamlit Secrets)*
- **Features:** Real-time query counters, latency graphs, model usage distribution, session browser, and dynamic document limit controls.

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
