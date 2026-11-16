"""Ollama provider adapter: a local model behind the inference interface.

Implements the provider-independent ``InferenceProvider`` protocol from
``genesis.inference.base`` against a local Ollama daemon, using only the
standard library, so the project keeps its zero-dependency core. A local
provider removes the hosted free tier's failure modes (withdrawn models,
rate limits) and keeps inference working offline on modest hardware, at
the cost of local CPU speed.

Configuration (constructor arguments win over environment variables):

- Model: ``GENESIS_OLLAMA_MODEL``, default ``llama3``.
- Base URL: ``OLLAMA_HOST``, default ``http://localhost:11434``.

No API key is involved: the daemon is the user's own process. Requests
disable Ollama's ``think`` mode because reasoning models otherwise spend
the output budget on hidden thinking and return an empty message within
small token limits (observed live with qwen3.5:2b, 17 Nov 2026).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Mapping

from genesis.inference.base import InferenceRequest, InferenceResponse
from genesis.inference.resources import TokenEstimator

DEFAULT_BASE_URL = "http://localhost:11434"
BASE_URL_ENV_VAR = "OLLAMA_HOST"
DEFAULT_MODEL = "llama3"
MODEL_ENV_VAR = "GENESIS_OLLAMA_MODEL"
# Local CPU inference is measured in minutes, not the seconds a hosted
# API needs; the default timeout reflects that.
DEFAULT_TIMEOUT_SECONDS = 600.0

# A transport performs one HTTP POST and returns (status, headers, body).
# Tests inject fakes; production uses the urllib default below.
Transport = Callable[[urllib.request.Request, float], "tuple[int, Mapping[str, str], bytes]"]


class OllamaError(RuntimeError):
    """Base class for Ollama provider failures."""


class OllamaUnavailableError(OllamaError):
    """Raised when the local Ollama daemon cannot be reached at all."""


class OllamaHTTPError(OllamaError):
    """Raised when the daemon answers with a non-success HTTP status."""

    def __init__(self, status: int, detail: str = ""):
        self.status = status
        message = f"Ollama request failed with HTTP {status}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


def _urllib_transport(request: urllib.request.Request, timeout: float) -> tuple[int, Mapping[str, str], bytes]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as error:
        # An HTTP error status is still a response; let generate() classify it.
        return error.code, dict(error.headers.items() if error.headers else {}), error.read()
    except urllib.error.URLError as error:
        raise OllamaUnavailableError(
            f"Cannot reach the Ollama daemon at {request.full_url}: {error.reason}"
        ) from error
    except TimeoutError as error:
        raise OllamaError("Ollama request timed out") from error


class OllamaProvider:
    """Chat-completion provider backed by a local Ollama daemon."""

    provider_name = "ollama"

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Transport | None = None,
        environ: Mapping[str, str] | None = None,
    ):
        env = os.environ if environ is None else environ
        resolved_model = model if model is not None else env.get(MODEL_ENV_VAR, "") or DEFAULT_MODEL
        if not resolved_model.strip():
            raise ValueError("model must be a non-empty Ollama model name")
        resolved_base_url = base_url if base_url is not None else env.get(BASE_URL_ENV_VAR, "") or DEFAULT_BASE_URL
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.model = resolved_model
        self.base_url = resolved_base_url.rstrip("/")
        self.timeout = float(timeout)
        self._transport = transport or _urllib_transport

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        if request.tier not in (0, 1, 2, 3):
            raise ValueError("tier must be between 0 and 3")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
            # Reasoning models spend the whole budget on hidden thinking
            # unless think mode is off; Genesis wants the answer itself.
            "think": False,
            "options": {"num_predict": request.max_output_tokens},
        }
        http_request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        status, _headers, body = self._transport(http_request, self.timeout)
        if not 200 <= status < 300:
            raise OllamaHTTPError(status, _error_detail(body))
        return self._parse_response(body, request)

    def _parse_response(self, body: bytes, request: InferenceRequest) -> InferenceResponse:
        try:
            data = json.loads(body.decode("utf-8"))
            text = data["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise OllamaError("Ollama returned a malformed response body") from error
        if not isinstance(text, str):
            raise OllamaError("Ollama returned a malformed response body")
        text = text.strip()
        if not text:
            raise OllamaError("Ollama returned an empty response")
        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")
        return InferenceResponse(
            text=text,
            provider=self.provider_name,
            model=data.get("model") or self.model,
            input_tokens=int(input_tokens) if input_tokens is not None else TokenEstimator.estimate(request.prompt),
            output_tokens=int(output_tokens) if output_tokens is not None else TokenEstimator.estimate(text),
        )


def _error_detail(body: bytes) -> str:
    """Best-effort short detail from an error body; never raises.

    Ollama error bodies carry ``error`` as a plain string, unlike the
    nested object most hosted APIs return, so both shapes are handled.
    """
    try:
        data = json.loads(body.decode("utf-8"))
        error = data.get("error", "")
        if isinstance(error, dict):
            return str(error.get("message", ""))[:200]
        return str(error)[:200]
    except Exception:
        return ""
