import http.client
import json
import re
import ssl
from time import monotonic

from mist.errors import ErrorCode, MistError
from mist.schemas import Envelope

HOST = "integrate.api.nvidia.com"
PATH = "/v1/chat/completions"
DESTINATION = "nvidia-integrate"
MAX_RESPONSE_BYTES = 1_000_000


class NvidiaProvider:
    """Fixed TLS destination; no redirects, retries, proxies, tools or streaming."""

    def __init__(self, api_key: str, *, timeout: float = 45.0, max_tokens: int = 512):
        if not isinstance(api_key, str) or not re.fullmatch(r"nvapi-[A-Za-z0-9_-]{20,200}", api_key):
            raise MistError(ErrorCode.PROVIDER_AUTH)
        if not 1 <= timeout <= 120 or not 1 <= max_tokens <= 4096:
            raise MistError(ErrorCode.CONFIGURATION)
        self._api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.last_usage: dict[str, int] | None = None
        self.last_finish_reason: str | None = None

    def generate(self, envelope: Envelope) -> str:
        self.last_usage = None
        self.last_finish_reason = None
        model = envelope.model
        if model.provider != "nvidia" or not model.external or model.destination != DESTINATION:
            raise MistError(ErrorCode.GUARD_BLOCKED)
        payload = {
            "model": model.model_id,
            "messages": [{"role": message.role.value, "content": message.content}
                         for message in envelope.request.messages],
            "max_tokens": self.max_tokens, "temperature": 0.2, "stream": False,
        }
        if model.enable_thinking is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": model.enable_thinking}
        connection = http.client.HTTPSConnection(HOST, timeout=self.timeout, context=ssl.create_default_context())
        deadline = monotonic() + self.timeout
        try:
            connection.request("POST", PATH, body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                               headers={"Authorization": "Bearer " + self._api_key,
                                        "Content-Type": "application/json", "Accept": "application/json"})
            response = connection.getresponse()
            if response.status in (401, 403):
                raise MistError(ErrorCode.PROVIDER_AUTH)
            if response.status == 429:
                raise MistError(ErrorCode.RATE_LIMIT)
            if response.status in (404, 410, 502, 503, 504):
                raise MistError(ErrorCode.PROVIDER_UNAVAILABLE)
            if response.status != 200:
                # Never read or expose an error body, location or response headers.
                raise MistError(ErrorCode.PROVIDER_FAILURE)
            if "application/json" not in response.getheader("Content-Type", "").lower():
                raise MistError(ErrorCode.INVALID_RESPONSE)
            chunks, size = [], 0
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise MistError(ErrorCode.PROVIDER_TIMEOUT)
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                chunk = response.read1(min(16384, MAX_RESPONSE_BYTES + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise MistError(ErrorCode.INVALID_RESPONSE)
                chunks.append(chunk)
            document = json.loads(b"".join(chunks))
            usage = document.get("usage") if isinstance(document, dict) else None
            if isinstance(usage, dict):
                metrics = {name: value for name in ("prompt_tokens", "completion_tokens", "total_tokens")
                           if type(value := usage.get(name)) is int and value >= 0}
                details = usage.get("completion_tokens_details")
                if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int:
                    if details["reasoning_tokens"] >= 0:
                        metrics["reasoning_tokens"] = details["reasoning_tokens"]
                self.last_usage = metrics or None
            choices = document["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise MistError(ErrorCode.INVALID_RESPONSE)
            choice = choices[0]
            reason = choice.get("finish_reason")
            if reason in ("stop", "length", "tool_calls", "content_filter"):
                self.last_finish_reason = reason
            message = choice["message"]
            text = message["content"]
            if (message.get("role") != "assistant" or message.get("tool_calls")
                    or message.get("function_call") or choice.get("finish_reason") != "stop"
                    or not isinstance(text, str) or not text.strip() or len(text) > 32000
                    or self._api_key in text):
                raise MistError(ErrorCode.INVALID_RESPONSE)
            return text
        except MistError:
            raise
        except TimeoutError:
            raise MistError(ErrorCode.PROVIDER_TIMEOUT) from None
        except (ValueError, KeyError, TypeError, AttributeError):
            raise MistError(ErrorCode.INVALID_RESPONSE) from None
        except (OSError, http.client.HTTPException):
            raise MistError(ErrorCode.PROVIDER_FAILURE) from None
        finally:
            connection.close()
