"""
modules/llm.py
Thin wrapper around the Azure OpenAI chat-completions endpoint.
All LLM calls in the application go through _llm_call().
"""

import json
import os
import urllib.error
import urllib.request


def _llm_available() -> bool:
    return (
        bool(os.environ.get("OPENAI_API_KEY", "").strip())
        and bool(os.environ.get("OPENAI_DEPLOYMENT_ENDPOINT", "").strip())
    )


def _llm_call(prompt: str, max_tokens: int = 300) -> str:
    endpoint = os.environ.get("OPENAI_DEPLOYMENT_ENDPOINT", "").rstrip("/")
    api_key  = os.environ.get("OPENAI_API_KEY", "")
    api_ver  = os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview")
    model    = os.environ.get("OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    url      = f"{endpoint}/openai/deployments/{model}/chat/completions?api-version={api_ver}"
    payload  = json.dumps({
        "messages":   [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"]
