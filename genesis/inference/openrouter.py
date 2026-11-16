"""OpenRouter provider adapter: a real model behind the inference interface.

OpenRouter exposes an OpenAI-compatible chat-completions API. This adapter
implements the provider-independent ``InferenceProvider`` protocol from
``genesis.inference.base`` using only the standard library, so the project
keeps its zero-dependency core. Any other provider (hosted or local) can be
swapped in behind the same ``generate`` contract without touching callers.

The API key is read from the ``OPENROUTER_API_KEY`` environment variable
unless one is passed explicitly. It is never hardcoded, logged, or included
in error messages.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Mapping

from genesis.inference.base import InferenceRequest, InferenceResponse
from genesis.inference.resources import TokenEstimator

API_KEY_ENV_VAR = "OPENROUTER_API_KEY"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
# A free-tier model available on OpenRouter at no cost; override per provider
# instance or via the GENESIS_OPENROUTER_MODEL environment variable.
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
MODEL_ENV_VAR = "GENESIS_OPENROUTER_MODEL"
DEFAULT_TIMEOUT_SECONDS = 30.0

# A transport performs one HTTP POST and returns (status, headers, body).
# Tests inject fakes; production uses the urllib default below.
Transport = Callable[[urllib.request.Request, float], "tuple[int, Mapping[str, str], bytes]"]


class OpenRouterError(RuntimeError):
    """Base class for OpenRouter adapter failures."""


class MissingAPIKeyError(OpenRouterError):
    """Raised when no API key is supplied or found in the environment."""


class OpenRouterHTTPError(OpenRouterError):
    """Raised for a non-success HTTP status other than 429."""

    def __init__(self, status: int, detail: str = ""):
        self.status = status
        message = f"OpenRouter request failed with HTTP {status}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


class RateLimitError(OpenRouterHTTPError):
    """Raised on HTTP 429; ``retry_after`` mirrors the Retry-After header."""

    def __init__(self, retry_after: float | None = None, detail: str = ""):
        self.retry_after = retry_after
        super().__init__(429, detail or "rate limit exceeded")


def _urllib_transport(request: urllib.request.Request, timeout: float) -> tuple[int, Mapping[str, str], bytes]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as error:
        # An HTTP error status is still a response; let generate() classify it.
        return error.code, dict(error.headers.items() if error.headers else {}), error.read()
    except urllib.error.URLError as error:
        raise OpenRouterError(f"OpenRouter request could not be sent: {error.reason}") from error
    except TimeoutError as error:
        raise OpenRouterError("OpenRouter request timed out") from error


class OpenRouterProvider:
    """Chat-completion provider backed by the OpenRouter API."""

    provider_name = "openrouter"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Transport | None = None,
        environ: Mapping[str, str] | None = None,
    ):
        env = os.environ if environ is None else environ
        key = api_key if api_key is not None else env.get(API_KEY_ENV_VAR, "")
        if not key or not key.strip():
            raise MissingAPIKeyError(
                f"No OpenRouter API key: pass api_key or set the {API_KEY_ENV_VAR} environment variable"
            )
        resolved_model = model if model is not None else env.get(MODEL_ENV_VAR, "") or DEFAULT_MODEL
        if not resolved_model.strip():
            raise ValueError("model must be a non-empty OpenRouter model id")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._api_key = key
        self.model = resolved_model
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self._transport = transport or _urllib_transport

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        if request.tier not in (0, 1, 2, 3):
            raise ValueError("tier must be between 0 and 3")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_output_tokens,
        }
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-Title": "Project Genesis",
            },
            method="POST",
        )
        status, headers, body = self._transport(http_request, self.timeout)
        if status == 429:
            raise RateLimitError(retry_after=_parse_retry_after(headers), detail=_error_detail(body))
        if not 200 <= status < 300:
            raise OpenRouterHTTPError(status, _error_detail(body))
        return self._parse_response(body, request)

    def _parse_response(self, body: bytes, request: InferenceRequest) -> InferenceResponse:
        try:
            data = json.loads(body.decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise OpenRouterError("OpenRouter returned a malformed response body") from error
        if not isinstance(text, str):
            raise OpenRouterError("OpenRouter returned a malformed response body")
        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        return InferenceResponse(
            text=text,
            provider=self.provider_name,
            model=data.get("model") or self.model,
            input_tokens=int(input_tokens) if input_tokens is not None else TokenEstimator.estimate(request.prompt),
            output_tokens=int(output_tokens) if output_tokens is not None else TokenEstimator.estimate(text),
        )


def _parse_retry_after(headers: Mapping[str, str]) -> float | None:
    for name, value in headers.items():
        if name.lower() == "retry-after":
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _error_detail(body: bytes) -> str:
    """Best-effort short detail from an error body; never raises."""
    try:
        data = json.loads(body.decode("utf-8"))
        message = data.get("error", {}).get("message", "")
        return str(message)[:200]
    except Exception:
        return ""
