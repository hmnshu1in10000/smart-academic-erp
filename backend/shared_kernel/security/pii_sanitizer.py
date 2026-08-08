"""
shared_kernel/security/pii_sanitizer.py
========================================
Local PII Sanitization Layer — strips phone numbers and email addresses
from any text before it leaves the application boundary toward an external LLM.

Design decisions:
- Pure stdlib (re) — no dependencies, no I/O.
- Regex patterns cover Indian mobile formats, international E.164 numbers,
  and RFC-5321-compliant email addresses.
- Runs in microseconds; safe to call on every LLM prompt.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Matches e-mail addresses (RFC-5321 local-part + domain)
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Phone number heuristic — runs AFTER email redaction.
# Covers:
#   +91-98765-43210  |  +919876543210  |  9876543210
#   +1 (800) 555-1234  |  022-12345678  |  0-800-123-4567
#   Not preceded by @ or word char (avoids matching inside email local-parts)
_PHONE_RE = re.compile(
    r"""
    (?<![a-zA-Z0-9@._\-])   # not inside an email address or word
    (?:\+?[\d]{1,4}          # optional country code (e.g. +91, +1, 0)
       [\s.\-]?              # optional separator
    )?
    (?:\(?[\d]{2,4}\)?       # optional area code in optional parens
       [\s.\-]?              # optional separator
    )?
    [\d]{3,5}                # first digit block (3-5 digits)
    [\s.\-]?                 # optional separator
    [\d]{4,5}                # second digit block (4-5 digits)
    (?![\d])                 # not followed by more digits
    """,
    re.VERBOSE,
)


def sanitize_prompt_for_llm(text: str) -> str:
    """
    Redact PII (phone numbers and email addresses) from *text* before it is
    sent to an external LLM API.

    Replacements:
      - Email addresses  → ``[EMAIL_REDACTED]``
      - Phone numbers    → ``[PHONE_REDACTED]``

    Parameters
    ----------
    text:
        The raw prompt string that may contain user-supplied content.

    Returns
    -------
    str
        A copy of *text* with all detected PII tokens replaced.
    """
    # Step 1: Redact emails first (the @ sign prevents the phone RE from
    # misidentifying email local-part digits as a phone number)
    text = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)

    # Step 2: Redact phone numbers
    text = _PHONE_RE.sub("[PHONE_REDACTED]", text)

    return text
