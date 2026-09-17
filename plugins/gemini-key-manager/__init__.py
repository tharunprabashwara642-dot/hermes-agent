"""Secure Gemini API-key pool management from Hermes slash commands.

The handler runs as a gateway/plugin command, before normal LLM routing. Raw
keys therefore never become part of an LLM prompt. Keys are persisted through
Hermes' existing credential-pool storage and benefit from its quota/rate-limit
rotation logic.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from agent.credential_pool import (
    AUTH_TYPE_API_KEY,
    PooledCredential,
    SOURCE_MANUAL,
    load_pool,
)

# Gemini / Google AI Studio keys commonly use the AIza prefix. Accept a broad
# token shape as well so future Google-issued key formats still work.
_GEMINI_KEY_RE = re.compile(r"^(?:AIza[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{24,})$")
_MAX_KEY_LENGTH = 512


def _extract_key(raw_args: str) -> Optional[str]:
    text = (raw_args or "").strip()
    if not text:
        return None
    # Accept a single token, or a friendly form such as:
    #   Gemini API key: AIza...
    #   add AIza...
    parts = text.split()
    if len(parts) == 1:
        candidate = parts[0]
    elif len(parts) == 2 and parts[0].lower() in {"add", "key", "gemini-key", "gemini"}:
        candidate = parts[1]
    else:
        # Last-resort extraction: take a unique Gemini-looking token only.
        matches = [p.strip("`\"'.,:;") for p in parts if _GEMINI_KEY_RE.fullmatch(p.strip("`\"'.,:;"))]
        if len(matches) != 1:
            return None
        candidate = matches[0]
    if not candidate or len(candidate) > _MAX_KEY_LENGTH:
        return None
    return candidate if _GEMINI_KEY_RE.fullmatch(candidate) else None


def _redacted(key: str) -> str:
    return f"…{key[-4:]}" if len(key) >= 4 else "…****"


def _handle_gemini_key(raw_args: str) -> str:
    key = _extract_key(raw_args)
    if not key:
        return (
            "Usage: /gemini-key <Gemini API key>\n"
            "Example: /gemini-key AIza...\n\n"
            "The key is added directly to Hermes' Gemini credential pool and "
            "is not sent to the model."
        )

    pool = load_pool("gemini")
    for entry in pool.entries():
        if entry.runtime_api_key == key:
            return f"Gemini key already exists in the pool ({_redacted(key)})."

    entry = PooledCredential(
        provider="gemini",
        id=uuid.uuid4().hex[:6],
        label=f"telegram-{key[-4:]}",
        auth_type=AUTH_TYPE_API_KEY,
        priority=0,
        source=f"{SOURCE_MANUAL}:telegram",
        access_token=key,
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    pool.add_entry(entry)

    count = len(pool.entries())
    return (
        f"✅ Gemini key added ({_redacted(key)}).\n"
        f"Gemini pool now has {count} credential(s).\n"
        "Automatic credential rotation remains enabled."
    )


def _handle_gemini_keys(raw_args: str) -> str:
    pool = load_pool("gemini")
    entries = pool.entries()
    if not entries:
        return "Gemini pool is empty."

    lines = [f"Gemini pool: {len(entries)} credential(s)"]
    for idx, entry in enumerate(entries, 1):
        token = entry.runtime_api_key
        suffix = token[-4:] if token else "????"
        state = entry.last_status or "ok"
        lines.append(f"{idx}. {entry.label or entry.id} (…{suffix}) — {state}")
    return "\n".join(lines)


def register(ctx) -> None:
    ctx.register_command(
        "gemini-key",
        handler=_handle_gemini_key,
        description="Add a Gemini API key to Hermes' secure credential pool.",
        args_hint="<api-key>",
    )
    ctx.register_command(
        "gemini-keys",
        handler=_handle_gemini_keys,
        description="Show the Gemini credential-pool status without revealing keys.",
    )
