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
# MODEL_PREMIUM: deepseek-v4-pro — deepest reasoning for summaries, risks, recommendations
# MODEL_QUALITY: kimi-k2p6 — balanced reasoning + speed for chat and conflict detection
# MODEL_FAST: deepseek-v4-flash — fast extraction/classification for matrix/questions
_MODEL_PREMIUM_DEFAULT = "accounts/fireworks/models/deepseek-v4-pro"
_MODEL_QUALITY_DEFAULT = "accounts/fireworks/models/kimi-k2p6"
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

        # 3-tier models — read from env vars so they can be overridden per-deployment
        # If PREMIUM is not set, falls back to QUALITY model
        self._model_premium = os.getenv("FIREWORKS_MODEL_PREMIUM", "")
        self._model_quality = os.getenv("FIREWORKS_MODEL_QUALITY", _MODEL_QUALITY_DEFAULT)
        self._model_fast = os.getenv("FIREWORKS_MODEL_FAST", _MODEL_FAST_DEFAULT)

        # If premium isn't configured, use quality model for premium tier too
        if not self._model_premium:
            self._model_premium = self._model_quality

        # Legacy fallback: if only FIREWORKS_MODEL is set, use it for all tiers
        legacy_model = os.getenv("FIREWORKS_MODEL", "")
        if legacy_model:
            if not os.getenv("FIREWORKS_MODEL_PREMIUM"):
                self._model_premium = legacy_model
            if not os.getenv("FIREWORKS_MODEL_QUALITY"):
                self._model_quality = legacy_model
            if not os.getenv("FIREWORKS_MODEL_FAST"):
                self._model_fast = legacy_model

        # Keep self._model for backward compatibility
        self._model = self._model_premium

        # Single-call mode: combine ALL analysis into ONE LLM call for extreme speed
        self._single_call_mode = os.getenv("SINGLE_CALL_MODE", "false").lower() == "true"

        # Semaphore: cap concurrent LLM calls at 3 to avoid Fireworks rate-limit cascades
        self._semaphore = asyncio.Semaphore(3)

        # Persistent async HTTP client — avoids TCP handshake overhead on every call.
        self._client = httpx.AsyncClient(
            timeout=180.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

        logger.info(f"Fireworks AI configured: endpoint={self._endpoint[:30]}...")
        logger.info(
            f"LLMService 3-tier models — premium: {self._model_premium}, "
            f"quality: {self._model_quality}, fast: {self._model_fast}"
        )
        logger.info("LLMService semaphore: max 5 concurrent LLM calls")
        if self._single_call_mode:
            logger.info("SINGLE_CALL_MODE enabled — all analysis in one mega-call")

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = 0.1,
        fast: bool = False,
        tier: str = "quality",
    ) -> str:
        """
        Send a completion request to Fireworks AI with automatic rate-limit retry
        and model fallback on 404.

        Args:
            fast: Legacy param. If True, uses FAST tier. Overridden by `tier`.
            tier: Model tier to use — "premium", "quality", or "fast".
                  - premium: deepseek-v4-pro (deepest reasoning — summaries, risks)
                  - quality: kimi-k2p6 (balanced — chat, conflicts)
                  - fast: deepseek-v4-flash (speed — matrix, quick scan)
        """
        # Legacy compat: if fast=True and tier wasn't explicitly changed, use fast
        if fast and tier == "quality":
            tier = "fast"

        # Build fallback chain: requested tier first, then others
        tier_order = [tier]
        for t in ["fast", "quality", "premium"]:
            if t not in tier_order:
                tier_order.append(t)

        last_error = None
        for try_tier in tier_order:
            async with self._semaphore:
                for attempt in range(3):
                    try:
                        return await self._call_fireworks(
                            system_prompt, user_prompt, max_tokens, temperature, tier=try_tier
                        )
                    except LLMRateLimitError:
                        if attempt < 2:
                            wait = (attempt + 1) * 2
                            logger.warning(
                                f"[Fireworks] Rate limited on tier={try_tier}, retry {attempt + 1}/3 in {wait}s..."
                            )
                            await asyncio.sleep(wait)
                        else:
                            last_error = LLMRateLimitError(f"Rate limit exhausted for tier={try_tier}")
                            break  # Try next tier
                    except LLMParseError as e:
                        if "404" in str(e):
                            logger.warning(f"[Fireworks] Model 404 for tier={try_tier}, trying fallback...")
                            last_error = e
                            break  # Try next tier
                        raise  # Non-404 parse errors are not retryable
                else:
                    continue  # Inner loop completed without break = success was returned above
                continue  # break from inner = try next tier

        # All tiers exhausted
        if last_error:
            raise last_error
        raise LLMRateLimitError("All model tiers exhausted")

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
        mega_prompt = f"""Analyze these sustainability/environmental documents for GREENWASHING and return ALL of the following in ONE JSON response.

DOCUMENTS: {doc_list}

{context}

Your job: Identify misleading sustainability claims, vague environmental promises, contradictions between documents, and gaps between marketing claims and actual data.

Return ONLY valid JSON with ALL these keys:
{{
  "executiveSummary": "<4-6 sentence greenwashing verdict: overall credibility score rationale, most serious greenwash red flag, specific claim-vs-data example, recommended consumer action>",
  "greenwashScore": <integer 0-100 where 0=total greenwashing, 100=fully credible>,
  "risks": [
    {{
      "id": "r1",
      "level": "HIGH|MEDIUM|LOW",
      "description": "<specific greenwashing risk or misleading claim identified>",
      "sourceDocument": "<filename where this was found>",
      "category": "<Misleading Claim|Vague Language|Missing Evidence|Contradiction|Cherry-Picking>"
    }}
  ],
  "comparisonMatrix": [
    {{
      "field": "<specific sustainability topic e.g. 'Carbon Offset Coverage'>",
      "values": {{"They Say": "<marketing claim>", "Data Shows": "<what data actually reveals>"}},
      "winner": "<'They Say' if claim is credible, 'Data Shows' if data contradicts, or null>"
    }}
  ],
  "recommendation": {{
    "title": "<action title for consumer/watchdog>",
    "summary": "<2-3 sentence recommendation on how to respond to these claims>",
    "nextSteps": ["step1", "step2", "step3"],
    "confidence": <0.0-1.0 how confident you are in this analysis>
  }},
  "suggestedQuestions": ["question1", "question2", "question3", "question4", "question5"],
  "conflicts": []
}}

SCORING GUIDE for greenwashScore:
- 0-30: HIGH RISK — multiple misleading claims, major contradictions, no third-party verification
- 31-60: MEDIUM RISK — vague claims, some unverified assertions, partial evidence gaps
- 61-100: LOW RISK — claims are specific, measurable, third-party verified, data-consistent

You MUST identify at least 3 risks and 3 comparison rows. Sustainability documents ALWAYS have claims that can be scrutinized.

CRITICAL: Output ONLY the JSON object. Do NOT include any thinking, reasoning, preamble, or explanation. Start your response with {{ and end with }}."""

        # Use FAST tier (deepseek-v4-flash) — reasoning models (kimi-k2p6) waste tokens
        # on <think> blocks before producing JSON, often causing truncation/parse failures.
        # Flash produces clean JSON directly and is 3-5x faster.
        raw = await self.complete(system_prompt, mega_prompt, max_tokens=max_tokens, temperature=0.0, tier="fast")
        raw = _strip_json_fences(raw)

        # Extra aggressive: find the LAST complete JSON object (skip any reasoning preamble)
        # The model often outputs thinking text then the JSON at the end
        import re as _re
        # Try to find the outermost JSON object that starts with {"executiveSummary"
        json_match = _re.search(r'\{[^{}]*"executiveSummary"', raw)
        if json_match:
            # Found likely start of our target JSON
            start_idx = json_match.start()
            # Find matching closing brace
            depth = 0
            end_idx = start_idx
            for i in range(start_idx, len(raw)):
                if raw[i] == '{':
                    depth += 1
                elif raw[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            if end_idx > start_idx:
                raw = raw[start_idx:end_idx + 1]

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            # Try to extract the outer JSON object
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                candidate = raw[brace_start:brace_end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass
                # Attempt JSON repair: fix trailing commas, unquoted nulls, etc.
                repaired = _repair_json(candidate)
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass
            logger.error(f"[Fireworks] Mega-call raw response (first 2000 chars): {raw[:2000]}")
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
        tier: str = "quality",
    ) -> str:
        """Execute a single Fireworks AI completion request using the persistent client."""
        # Resolve model from tier
        if fast and tier == "quality":
            tier = "fast"
        if tier == "premium":
            model = self._model_premium
        elif tier == "fast":
            model = self._model_fast
        else:
            model = self._model_quality

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
            # Model not found (404) — try falling back to a different tier
            if "404" in str(exc.response.status_code):
                logger.error(
                    f"[Fireworks] Model '{model}' returned 404. "
                    f"Check that the model ID is correct and available on your account. "
                    f"Full error: {exc}"
                )
                raise LLMParseError(
                    f"Model '{model}' not found on Fireworks AI (404). "
                    f"Verify FIREWORKS_MODEL_PREMIUM, FIREWORKS_MODEL_QUALITY, and FIREWORKS_MODEL_FAST "
                    f"environment variables point to valid model IDs."
                ) from exc
            raise

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        content = _sanitize_unicode(content)
        logger.info(
            f"[Fireworks/AMD] Response received ({len(content)} chars) tier={tier}"
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


def _repair_json(text: str) -> str:
    """Attempt to repair common LLM JSON formatting issues.

    Handles:
    - Trailing commas before } or ]
    - Single-line // comments
    - Unescaped newlines inside strings
    - Truncated JSON (close all open braces/brackets)
    """
    # Remove single-line comments (// ...) that are NOT inside strings
    # Simple heuristic: remove lines that are only comments
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('//'):
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Try to close unclosed braces/brackets (truncated responses)
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    if open_braces > 0 or open_brackets > 0:
        # Truncate to last complete value (last comma or colon+value)
        # Then close remaining brackets
        text = text.rstrip()
        # Remove trailing incomplete key-value
        if text and text[-1] not in ('}', ']', '"', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'e', 'l', 'u'):
            last_comma = text.rfind(',')
            if last_comma > 0:
                text = text[:last_comma]
        text += ']' * max(0, open_brackets) + '}' * max(0, open_braces)

    return text


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences, thinking tags, and extract JSON from verbose LLM responses.

    Some models often prefix responses with prose like 'Here is the JSON:' or
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
