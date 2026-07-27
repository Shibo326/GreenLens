import asyncio
import json
import logging
import os
import re
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_TOKENS_DEFAULT = 800

# ── Tiered model config ──────────────────────────────────────────────────────
# MODEL_QUALITY: deepseek-v4-pro — top reasoning model for summaries, risks, recommendations
# MODEL_FAST: deepseek-v4-flash — fast extraction/classification for matrix/questions/conflicts
_MODEL_QUALITY_DEFAULT = "accounts/fireworks/models/deepseek-v4-pro"
_MODEL_FAST_DEFAULT = "accounts/fireworks/models/deepseek-v4-flash"


class LLMRateLimitError(Exception):
    """Raised when the LLM provider returns a rate limit / quota exceeded error."""
    pass


class LLMParseError(Exception):
    """Raised when LLM response cannot be parsed into the expected model."""
    pass


class LLMService:
    """
    LLM service using Fireworks AI (AMD MI300X hardware).
    All inference runs on AMD MI300X via the Fireworks platform.

    Performance optimizations applied:
    - Tiered model routing: deepseek-v4-pro for reasoning, deepseek-v4-flash for structured output
    - Semaphore cap (max 3 concurrent calls) to avoid rate-limit cascades
    - Persistent httpx.AsyncClient with connection pooling (avoids TCP handshake per call)
    - Tuned temperatures (0.1 for structured JSON outputs)
    - Reduced max_tokens where safe to do so
    - SINGLE_CALL_MODE env var for emergency single-mega-call fallback
    """

    def __init__(self):
        self._api_key = os.getenv("FIREWORKS_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "FIREWORKS_API_KEY is required. "
                "Set it in your .env file or Railway environment variables. "
                "Get a key at https://app.fireworks.ai/settings/api-keys"
            )
        self._endpoint = os.getenv("FIREWORKS_ENDPOINT", "https://api.fireworks.ai/inference/v1")
        if not self._endpoint:
            raise ValueError(
                "FIREWORKS_ENDPOINT is required. "
                "Set it in your .env file or Railway environment variables."
            )

        # Vision model — optional, used for /chat/vision endpoint
        self._model_vision = os.getenv("FIREWORKS_MODEL_VISION", "")

        # Tiered models — read from env vars so they can be overridden per-deployment
        self._model_quality = os.getenv("FIREWORKS_MODEL_QUALITY", _MODEL_QUALITY_DEFAULT)
        self._model_fast = os.getenv("FIREWORKS_MODEL_FAST", _MODEL_FAST_DEFAULT)

        # Legacy fallback: if only FIREWORKS_MODEL is set, use it for both tiers
        legacy_model = os.getenv("FIREWORKS_MODEL", "")
        if legacy_model:
            if not os.getenv("FIREWORKS_MODEL_QUALITY"):
                self._model_quality = legacy_model
            if not os.getenv("FIREWORKS_MODEL_FAST"):
                self._model_fast = legacy_model

        # Keep self._model for backward compatibility
        self._model = self._model_quality

        # Single-call mode: combine ALL analysis into ONE LLM call for extreme speed
        self._single_call_mode = os.getenv("SINGLE_CALL_MODE", "false").lower() == "true"

        # Semaphore: cap concurrent LLM calls at 3 to prevent rate-limit cascades.
        # Our 5 parallel analysis tasks will queue up rather than all hitting the API at once.
        self._semaphore = asyncio.Semaphore(3)

        # Persistent async HTTP client — avoids TCP handshake overhead on every call.
        # limits: 20 keepalive connections, up to 100 concurrent (covers our 5 parallel calls easily).
        self._client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

        logger.info(f"Fireworks AI configured: endpoint={self._endpoint[:30]}...")
        logger.info(
            f"LLMService tiered models — quality: {self._model_quality}, fast: {self._model_fast}"
        )
        logger.info("LLMService semaphore: max 3 concurrent LLM calls")
        if self._single_call_mode:
            logger.info("SINGLE_CALL_MODE enabled — all analysis in one mega-call")

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = 0.1,
        fast: bool = False,
    ) -> str:
        """
        Send a completion request to Fireworks AI with automatic rate-limit retry.

        Args:
            fast: If True, uses MODEL_FAST (gpt-oss-120b) for structured/speed tasks.
                  If False (default), uses MODEL_QUALITY (deepseek-v4-flash) for reasoning.
        """
        async with self._semaphore:
            for attempt in range(3):
                try:
                    return await self._call_fireworks(
                        system_prompt, user_prompt, max_tokens, temperature, fast=fast
                    )
                except LLMRateLimitError:
                    if attempt < 2:
                        wait = (attempt + 1) * 2  # 2s then 4s
                        logger.warning(
                            f"[Fireworks] Rate limited, retry {attempt + 1}/3 in {wait}s..."
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error("[Fireworks] Rate limit — all retries exhausted")
                        raise
        raise LLMRateLimitError("Max retries exceeded")

    async def single_mega_call(
        self,
        system_prompt: str,
        context: str,
        doc_names: list[str],
        max_tokens: int = 4000,
    ) -> dict:
        """
        SINGLE_CALL_MODE: combine ALL analysis into ONE LLM call.
        Trades some quality for extreme speed (1 API call instead of 5).
        Used as emergency fallback when SINGLE_CALL_MODE=true.

        Returns a dict with all analysis fields, or raises on failure.
        """
        doc_list = ", ".join(doc_names)
        mega_prompt = f"""Analyze these documents and return ALL of the following in ONE JSON response.

DOCUMENTS: {doc_list}

{context}

Return ONLY valid JSON with ALL these keys:
{{
  "executiveSummary": "<4-6 sentence executive briefing with specific figures, urgency, and recommended direction>",
  "risks": [
    {{
      "id": "r1",
      "level": "HIGH|MEDIUM|LOW",
      "description": "<specific risk>",
      "sourceDocument": "<filename>",
      "category": "<category>"
    }}
  ],
  "comparisonMatrix": [
    {{
      "field": "<comparison dimension>",
      "values": {{"<DocName>": "<value>"}},
      "winner": "<best option or null>"
    }}
  ],
  "recommendation": {{
    "title": "<action title>",
    "summary": "<2-3 sentence recommendation>",
    "nextSteps": ["step1", "step2", "step3"],
    "confidence": 0.8
  }},
  "suggestedQuestions": ["question1", "question2", "question3", "question4", "question5"],
  "conflicts": []
}}"""

        raw = await self.complete(system_prompt, mega_prompt, max_tokens=max_tokens, fast=False)
        raw = _strip_json_fences(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            # Try to extract the outer JSON object
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                try:
                    return json.loads(raw[brace_start:brace_end + 1])
                except json.JSONDecodeError:
                    pass
            raise LLMParseError(f"Mega-call JSON parse failed: {e}") from e

    async def aclose(self) -> None:
        """Close the persistent HTTP client. Call on app shutdown."""
        await self._client.aclose()

    async def complete_vision(
        self,
        system_prompt: str,
        user_text: str,
        image_base64: str,
        image_mime: str,
        max_tokens: int = 800,
    ) -> str:
        """
        Send a vision completion request using OpenAI-compatible multi-part message format.

        Requires FIREWORKS_MODEL_VISION to be configured.
        """
        if not self._model_vision:
            raise LLMParseError(
                "FIREWORKS_MODEL_VISION not configured. "
                "Set it in your .env file to enable vision analysis."
            )

        async with self._semaphore:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload = {
                "model": self._model_vision,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime};base64,{image_base64}",
                                },
                            },
                        ],
                    },
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            }

            try:
                response = await self._client.post(
                    f"{self._endpoint}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                exc_str = str(exc).lower()
                if "429" in exc_str or "rate limit" in exc_str:
                    raise LLMRateLimitError(f"Fireworks rate limit (vision): {exc}") from exc
                raise

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            content = _sanitize_unicode(content)
            logger.info(f"[Fireworks/AMD] Vision response received ({len(content)} chars)")
            return content

    async def _call_fireworks(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        fast: bool = False,
    ) -> str:
        """Execute a single Fireworks AI completion request using the persistent client."""
        model = self._model_fast if fast else self._model_quality
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
        }

        try:
            response = await self._client.post(
                f"{self._endpoint}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate limit" in exc_str:
                raise LLMRateLimitError(f"Fireworks rate limit: {exc}") from exc
            raise

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        content = _sanitize_unicode(content)
        logger.info(
            f"[Fireworks/AMD] Response received ({len(content)} chars) model={'fast' if fast else 'quality'}"
        )
        return content

    async def _parse_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        model_class: Type[T],
        max_tokens: int = MAX_TOKENS_DEFAULT,
    ) -> T:
        """
        Call LLM and parse into a Pydantic model.
        Retries once with a correction prompt if the first parse fails.
        """
        raw = await self.complete(system_prompt, user_prompt, max_tokens)
        raw = _strip_json_fences(raw)

        try:
            return model_class.model_validate_json(raw)
        except (ValidationError, Exception) as first_error:
            logger.warning(f"First parse attempt failed: {first_error}. Retrying.")
            corrective_prompt = (
                user_prompt
                + "\n\nIMPORTANT: Your previous response contained invalid JSON. "
                "Respond ONLY with valid JSON matching the exact schema. "
                "Do not include any text outside the JSON object."
            )
            raw2 = await self.complete(system_prompt, corrective_prompt, max_tokens)
            raw2 = _strip_json_fences(raw2)

            try:
                return model_class.model_validate_json(raw2)
            except (ValidationError, Exception) as second_error:
                raise LLMParseError(
                    f"LLM failed to produce valid JSON after retry: {second_error}"
                ) from second_error


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences, thinking tags, and extract JSON from verbose LLM responses.

    gpt-oss-120b often prefixes responses with prose like 'Here is the JSON:' or
    'Based on my analysis, here is the result:' before the actual JSON block.
    This function strips all such preamble and returns only the JSON content.
    """
    text = text.strip()
    # Strip <think>...</think> blocks (DeepSeek/Kimi reasoning models)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.strip()
    # Strip [think]...[/think] variant
    text = re.sub(r'\[think\].*?\[/think\]', '', text, flags=re.DOTALL)
    text = text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines)
    text = text.strip()
    # Strip any remaining closing fence that may be left
    if text.endswith("```"):
        text = text[:-3].strip()
    # If the text doesn't start with { or [, try to find JSON in the response.
    # This handles gpt-oss-120b's habit of prefixing responses with prose preamble
    # like "Here is the JSON:", "Based on my analysis:", "Certainly! Here is:", etc.
    if text and text[0] not in ('{', '['):
        # Look for the first { or [ and extract from there
        json_start = -1
        for i, ch in enumerate(text):
            if ch in ('{', '['):
                json_start = i
                break
        if json_start >= 0:
            # Find the matching closing bracket
            candidate = text[json_start:]
            bracket = candidate[0]
            close_bracket = '}' if bracket == '{' else ']'
            # Find the last occurrence of the closing bracket
            last_close = candidate.rfind(close_bracket)
            if last_close > 0:
                candidate = candidate[:last_close + 1]
            text = candidate
    text = text.strip()
    # Remove control characters that break JSON parsing (keep \n and \t as escaped)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text


def _sanitize_unicode(text: str) -> str:
    """
    Replace problematic Unicode characters that render as black boxes/squares
    in web fonts (Inter, system fonts) with their ASCII equivalents.

    Common culprits from LLM outputs:
    - \u2010 (hyphen), \u2011 (non-breaking hyphen), \u2012 (figure dash) -> regular hyphen
    - \u2013 (en-dash), \u2014 (em-dash) -> kept as-is (most fonts support these)
    - \u00AD (soft hyphen) -> removed
    - \u200B (zero-width space), \u200C, \u200D, \uFEFF (BOM) -> removed
    - \u2018, \u2019 (smart single quotes) -> regular apostrophe
    - \u201C, \u201D (smart double quotes) -> regular double quote
    """
    if not text:
        return text
    # Replace uncommon hyphens with regular hyphen
    text = text.replace('\u2010', '-')  # hyphen
    text = text.replace('\u2011', '-')  # non-breaking hyphen
    text = text.replace('\u2012', '-')  # figure dash
    # Remove soft hyphen and zero-width characters
    text = text.replace('\u00AD', '')   # soft hyphen
    text = text.replace('\u200B', '')   # zero-width space
    text = text.replace('\u200C', '')   # zero-width non-joiner
    text = text.replace('\u200D', '')   # zero-width joiner
    text = text.replace('\uFEFF', '')   # BOM / zero-width no-break space
    # Smart quotes -> regular quotes
    text = text.replace('\u2018', "'")  # left single quote
    text = text.replace('\u2019', "'")  # right single quote
    text = text.replace('\u201C', '"')  # left double quote
    text = text.replace('\u201D', '"')  # right double quote
    # Replace other problematic dashes that some fonts can't render
    text = text.replace('\u2015', '\u2014')  # horizontal bar -> em-dash
    text = text.replace('\u2212', '-')  # minus sign -> hyphen
    return text
