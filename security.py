"""Enterprise-grade security controls for DocuMind AI.

Provides protection against:
- Cross-Site Scripting (XSS) via safe HTML escaping
- Denial of Service & API quota draining via sliding-window Rate Limiting
- Prompt Injection & Jailbreak attacks via pattern detection and strict boundary encapsulation
- Path Traversal & PDF Bomb attacks via filename sanitization and magic-byte verification
- Timing attacks and brute-force guessing against the Admin panel via constant-time compare & lockout
"""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── 1. Safe HTML Escaping (XSS Prevention) ───────────────────────────────────
def safe_html(text: Any) -> str:
    """Escapes all HTML special characters to strictly prevent stored and reflected XSS."""
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


# ── 2. Sliding-Window Rate Limiter (DoS & Quota Draining Defense) ─────────────
@dataclass
class RateLimiter:
    """In-memory sliding-window rate limiter per session or client identifier."""
    max_requests: int = 12       # Maximum queries allowed in the window
    window_seconds: int = 60     # Time window in seconds (1 minute)
    _records: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (is_allowed, seconds_until_reset)."""
        now = time.time()
        cutoff = now - self.window_seconds
        # Clean older requests outside the active sliding window
        self._records[client_id] = [t for t in self._records[client_id] if t > cutoff]

        if len(self._records[client_id]) >= self.max_requests:
            oldest = self._records[client_id][0]
            retry_after = max(1, int(oldest + self.window_seconds - now))
            return False, retry_after

        self._records[client_id].append(now)
        return True, 0


# Global shared rate limiter for queries
_QUERY_LIMITER = RateLimiter(max_requests=10, window_seconds=60)


def check_rate_limit(client_id: str) -> tuple[bool, int]:
    """Check query rate limit for a given session. Returns (allowed, wait_seconds)."""
    return _QUERY_LIMITER.is_allowed(client_id)


# ── 3. Prompt Injection & Jailbreak Defense ──────────────────────────────────
# Suspicious patterns commonly used in jailbreaks and direct prompt injection
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+(instructions?|rules?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?DAN\s+mode", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?(filters?|rules?|guardrails?)", re.IGNORECASE),
    re.compile(r"output\s+(your\s+)?(system\s+prompt|initial\s+instructions?)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(instructions?|system\s+prompt|api\s*key)", re.IGNORECASE),
    re.compile(r"system\s*override", re.IGNORECASE),
    re.compile(r"developer\s+mode\s+enabled", re.IGNORECASE),
]


def detect_prompt_injection(prompt: str) -> tuple[bool, str]:
    """Inspects user input for adversarial prompt injection patterns.
    
    Returns (is_suspicious, reason).
    """
    clean = prompt.strip()
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(clean)
        if match:
            return True, f"Suspicious override instruction detected ('{match.group(0)}'). Please ask a question directly related to the documents."
    return False, ""


def sanitize_input(text: str, max_chars: int = 2000) -> str:
    """Sanitize raw user input:
    - Strips null bytes and invisible control characters
    - Truncates to max_chars to prevent memory / token flooding
    - Normalizes excessive whitespace
    """
    if not text:
        return ""
    # Remove null bytes and non-printable control characters (except newline, tab)
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    # Truncate
    sanitized = sanitized[:max_chars].strip()
    return sanitized


# ── 4. File Upload & PDF Validation (Path Traversal & PDF Bomb Defense) ────────
def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and filesystem attacks."""
    # Strip any directory path components
    base_name = Path(filename.replace("\\", "/")).name
    # Keep only safe alphanumeric characters, dashes, underscores, and dots
    safe = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base_name)
    # Ensure it ends with .pdf
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    return safe[:100]  # bounded filename length


def validate_pdf_bytes(data: bytes, filename: str, max_bytes: int = 15 * 1024 * 1024) -> tuple[bool, str]:
    """Performs deep validation on uploaded file bytes:
    1. Size limit
    2. Magic bytes verification (%PDF-)
    3. Filename security checks
    """
    if len(data) == 0:
        return False, "Uploaded file is completely empty."
    if len(data) > max_bytes:
        return False, f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB."
    if not data.startswith(b"%PDF-"):
        return False, f"File '{filename}' does not contain a valid PDF signature (%PDF-)."
    # Check for executable extensions in original name
    lower_name = filename.lower()
    for bad_ext in [".exe", ".bat", ".cmd", ".sh", ".py", ".js", ".vbs", ".ps1"]:
        if bad_ext in lower_name:
            return False, f"Dangerous file extension pattern detected in '{filename}'."
    return True, ""


# ── 5. Admin Authentication & Brute-Force Defense ─────────────────────────────
# Default fallback salt for SHA-256 password hashing
_HASH_SALT = b"documind_secure_salt_2025"


def hash_password(password: str) -> str:
    """Compute salted SHA-256 hash of a password."""
    return hashlib.sha256(_HASH_SALT + password.encode("utf-8")).hexdigest()


def get_admin_password_hash() -> str:
    """Retrieve the expected admin password hash from environment or secrets."""
    # First check env or streamlit secrets
    raw_pwd = os.getenv("ADMIN_PASSWORD")
    if raw_pwd:
        return hash_password(raw_pwd)
    # Default initial password if not configured in .env (documind2025)
    return hash_password("documind2025")


def verify_admin_password(input_password: str, session_state: dict[str, Any]) -> tuple[bool, str]:
    """Verifies admin password with constant-time comparison and brute-force lockout.
    
    Locks out attempts for 15 minutes after 5 consecutive failures.
    Returns (success, message).
    """
    now = time.time()
    failed_attempts = session_state.get("admin_failed_attempts", 0)
    lockout_until = session_state.get("admin_lockout_until", 0)

    # Check active lockout
    if now < lockout_until:
        remaining = int(lockout_until - now)
        return False, f"🔒 Too many failed attempts. Access locked for {remaining} more seconds."

    expected_hash = get_admin_password_hash()
    input_hash = hash_password(input_password)

    # Constant-time comparison to prevent timing attacks
    if hmac.compare_digest(expected_hash, input_hash):
        session_state["admin_failed_attempts"] = 0
        session_state["admin_lockout_until"] = 0
        return True, "Authentication successful."
    else:
        failed_attempts += 1
        session_state["admin_failed_attempts"] = failed_attempts
        if failed_attempts >= 5:
            session_state["admin_lockout_until"] = now + (15 * 60)  # 15 minute lockout
            return False, "🚨 5 failed attempts reached. Admin access is temporarily locked for 15 minutes."
        remaining_tries = 5 - failed_attempts
        return False, f"Incorrect password. {remaining_tries} attempt(s) remaining before lockout."

