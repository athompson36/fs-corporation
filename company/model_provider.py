"""Live text model providers. Credentials stay in env, not prompts or SQLite."""
from __future__ import annotations
import os

import httpx

OPENAI_PROVIDERS = frozenset({"openai", "openai-compatible", "configure-provider"})
ANTHROPIC_PROVIDERS = frozenset({"anthropic", "claude"})
LIVE_PROVIDERS = OPENAI_PROVIDERS | ANTHROPIC_PROVIDERS

ANTHROPIC_API = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"


def _raise_for_provider(response: httpx.Response, provider: str, model: str) -> None:
    if response.status_code == 404:
        raise LookupError(
            f"Model {model!r} not found for {provider}; "
            "list available model ids from the provider API (see deploy/dev/README.md)")
    response.raise_for_status()


def _max_tokens() -> int:
    return int(os.environ.get("MODEL_PROVIDER_MAX_TOKENS") or "512")


def openai_configured() -> bool:
    return bool((os.environ.get("MODEL_PROVIDER_API_KEY") or "").strip())


def anthropic_configured() -> bool:
    return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())


def model_configured() -> bool:
    return openai_configured() or anthropic_configured()


def _openai_base_url() -> str:
    return (os.environ.get("MODEL_PROVIDER_BASE_URL") or "https://api.openai.com/v1").rstrip("/")


def _openai_api_key() -> str:
    value = (os.environ.get("MODEL_PROVIDER_API_KEY") or "").strip()
    if not value:
        raise NotImplementedError("MODEL_PROVIDER_API_KEY is not configured")
    return value


def _anthropic_api_key() -> str:
    value = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not value:
        raise NotImplementedError("ANTHROPIC_API_KEY is not configured")
    return value


def _credential_env(profile: dict) -> str:
    ref = (profile.get("credential_ref") or "").strip()
    if ref == "ANTHROPIC_API_KEY":
        return "ANTHROPIC_API_KEY"
    if ref == "MODEL_PROVIDER_API_KEY":
        return "MODEL_PROVIDER_API_KEY"
    provider = profile.get("provider")
    if provider in ANTHROPIC_PROVIDERS:
        return "ANTHROPIC_API_KEY"
    return "MODEL_PROVIDER_API_KEY"


def _require_credential(profile: dict) -> None:
    env_name = _credential_env(profile)
    if not (os.environ.get(env_name) or "").strip():
        raise NotImplementedError(f"Live model requires {env_name} inside the worker boundary")


def _openai_status() -> dict:
    if not openai_configured():
        return {"configured": False, "live": False}
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{_openai_base_url()}/models",
                headers={"Authorization": f"Bearer {_openai_api_key()}"},
            )
        if response.status_code == 401:
            return {"configured": True, "live": False, "error": "invalid API key", "base_url": _openai_base_url()}
        response.raise_for_status()
        return {"configured": True, "live": True, "base_url": _openai_base_url()}
    except Exception as exc:
        return {"configured": True, "live": False, "error": str(exc), "base_url": _openai_base_url()}


def _anthropic_status(*, probe: bool = False) -> dict:
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return {"configured": False, "live": False}
    if not probe:
        plausible = key.startswith("sk-ant-")
        out = {"configured": True, "live": plausible}
        if not plausible:
            out["error"] = "unexpected API key format"
        return out
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{ANTHROPIC_API}/v1/models",
                headers={"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION},
            )
        if response.status_code == 401:
            return {"configured": True, "live": False, "error": "invalid API key"}
        response.raise_for_status()
        models = [m.get("id") for m in response.json().get("data", []) if m.get("id")]
        return {"configured": True, "live": bool(models), "models_available": len(models)}
    except Exception as exc:
        return {"configured": True, "live": False, "error": str(exc)}


def status_summary(*, probe: bool = False) -> dict:
    openai = _openai_status()
    anthropic = _anthropic_status(probe=probe)
    configured = openai["configured"] or anthropic["configured"]
    live = openai.get("live") or anthropic.get("live")
    summary = {
        "configured": configured,
        "live": bool(live),
        "openai": openai,
        "anthropic": anthropic,
    }
    if openai.get("live"):
        summary["base_url"] = openai.get("base_url")
    return summary


def _complete_openai(profile_id: str, profile: dict, prompt: str) -> dict:
    _require_credential(profile)
    model = (profile.get("model") or "").strip()
    if not model or model.startswith("configure-"):
        raise NotImplementedError("Profile model id is not configured")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": _max_tokens(),
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{_openai_base_url()}/chat/completions",
            headers={"Authorization": f"Bearer {_openai_api_key()}"},
            json=body,
        )
        _raise_for_provider(response, "openai", model)
        payload = response.json()
    choice = (payload.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    usage = payload.get("usage") or {}
    cost = int(usage.get("total_tokens") or 0)
    return {
        "text": text,
        "profile_id": profile_id,
        "cost_cents": cost,
        "provider": profile.get("provider"),
        "model": model,
    }


def _complete_anthropic(profile_id: str, profile: dict, prompt: str) -> dict:
    _require_credential(profile)
    model = (profile.get("model") or "").strip()
    if not model or model.startswith("configure-"):
        raise NotImplementedError("Profile model id is not configured")
    body = {
        "model": model,
        "max_tokens": _max_tokens(),
        "messages": [{"role": "user", "content": prompt}],
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{ANTHROPIC_API}/v1/messages",
            headers={
                "x-api-key": _anthropic_api_key(),
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=body,
        )
        _raise_for_provider(response, "anthropic", model)
        payload = response.json()
    parts = payload.get("content") or []
    text = "".join(
        block.get("text", "") for block in parts if isinstance(block, dict) and block.get("type") == "text"
    ).strip()
    usage = payload.get("usage") or {}
    cost = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
    return {
        "text": text,
        "profile_id": profile_id,
        "cost_cents": cost,
        "provider": profile.get("provider"),
        "model": model,
    }


def complete(profile_id: str, profile: dict, prompt: str) -> dict:
    if profile.get("provider") == "mock":
        raise ValueError("Use invoke_model mock path for mock provider")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt required")
    provider = profile.get("provider")
    if provider in OPENAI_PROVIDERS:
        return _complete_openai(profile_id, profile, prompt)
    if provider in ANTHROPIC_PROVIDERS:
        return _complete_anthropic(profile_id, profile, prompt)
    raise NotImplementedError(f"Unsupported model provider: {provider}")
