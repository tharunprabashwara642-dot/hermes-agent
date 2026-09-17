"""Google Gemini provider profiles.

gemini:            Google AI Studio (API key) — uses GeminiNativeClient

Reports api_mode="chat_completions" but uses a custom native client
that bypasses the standard OpenAI transport. The profile captures auth
and endpoint metadata for auth.py / runtime_provider.py migration, and
carries the thinking_config translation hook so the transport's profile
path produces the same extra_body shape the legacy flag path did.

Multi-key support:
    GEMINI_API_KEY
    GEMINI_API_KEY_2
    GEMINI_API_KEY_3
    ...

Google's historical alias is also supported:
    GOOGLE_API_KEY
    GOOGLE_API_KEY_2
    GOOGLE_API_KEY_3
    ...

The credential-pool layer already handles round-robin selection and
429/402/401 rotation. This provider profile exposes the numbered env
siblings to that existing pool without storing the raw keys in auth.json.
"""

from typing import Any

from providers import register_provider
from providers.base import ProviderProfile


# Keep the pool practical for hosted environments while providing a large
# numbered key range. Users with more credentials can still add them through
# `hermes auth add gemini --api-key ...`, which uses the same pool.
_MAX_NUMBERED_GEMINI_KEYS = 256


def _numbered_env_vars(base_name: str) -> tuple[str, ...]:
    return (base_name,) + tuple(
        f"{base_name}_{index}" for index in range(2, _MAX_NUMBERED_GEMINI_KEYS + 1)
    )


GEMINI_API_KEY_ENV_VARS = (
    _numbered_env_vars("GEMINI_API_KEY")
    + _numbered_env_vars("GOOGLE_API_KEY")
)


class GeminiProfile(ProviderProfile):
    """Gemini — translate reasoning_config to thinking_config in extra_body."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context: Any
    ) -> dict[str, Any]:
        """Emit extra_body.thinking_config (native) or extra_body.extra_body.google.thinking_config
        (OpenAI-compat /openai subpath), mirroring the legacy path's behavior.
        """
        from agent.transports.chat_completions import (
            _build_gemini_thinking_config,
            _is_gemini_openai_compat_base_url,
            _snake_case_gemini_thinking_config,
        )

        model = context.get("model") or ""
        reasoning_config = context.get("reasoning_config")
        base_url = context.get("base_url") or self.base_url

        raw_thinking_config = _build_gemini_thinking_config(model, reasoning_config)
        if not raw_thinking_config:
            return {}

        body: dict[str, Any] = {}
        if self.name == "gemini" and _is_gemini_openai_compat_base_url(base_url):
            thinking_config = _snake_case_gemini_thinking_config(raw_thinking_config)
            if thinking_config:
                body["extra_body"] = {"google": {"thinking_config": thinking_config}}
        else:
            body["thinking_config"] = raw_thinking_config
        return body


gemini = GeminiProfile(
    name="gemini",
    aliases=("google", "google-gemini", "google-ai-studio"),
    api_mode="chat_completions",
    env_vars=GEMINI_API_KEY_ENV_VARS,
    base_url="https://generativelanguage.googleapis.com/v1beta",
    auth_type="api_key",
    default_aux_model="gemini-3.5-flash",
)

register_provider(gemini)