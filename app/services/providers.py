from __future__ import annotations


def normalize_provider(value: str, default: str = "auto") -> str:
    provider = (value or default or "auto").strip().lower()
    if provider not in {"auto", "local", "api"}:
        return "auto"
    return provider


def should_try_api(selected: str, api_configured: bool) -> bool:
    provider = normalize_provider(selected)
    return api_configured and provider in {"auto", "api"}


def should_try_local(selected: str) -> bool:
    provider = normalize_provider(selected)
    return provider in {"auto", "local", "api"}
