import json
import logging
import time
import uuid

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio

from models.response import (
    ChatRequest,
    ChatResponse,
    Evidence,
    StructuredAIResponse,
)
from prompts.chat_copilot import build_chat_prompt
from prompts.system_prompt import get_system_prompt
from services.embedding_service import EmbeddingService
from services.llm_service import LLMService, _strip_json_fences
from services.session_manager import SessionManager, SessionNotFoundError
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances (set from main.py at startup)
_embedding_service: EmbeddingService | None = None
_vector_store: VectorStore | None = None
_session_manager: SessionManager | None = None
_llm_service: LLMService | None = None


def _err(status: int, message: str, code: str, suggestion: str = ""):
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "suggestion": suggestion or None},
    )


def _check_services():
    """Return an error response if services are not initialized, or None if ready."""
    if _embedding_service is None or _vector_store is None or _session_manager is None or _llm_service is None:
        return _err(503, "Service is starting up. Please try again in a moment.", "SERVICE_UNAVAILABLE", "The server is still initializing. Please retry in 10-20 seconds.")
    return None


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Answer a natural language question about the uploaded documents using hybrid RAG.

    Embeds the question, retrieves top-8 relevant chunks, supplements with full context
    if needed, then uses both document evidence and expert LLM knowledge to produce
    a structured, professional response with citations and recommendations.
    """
    embedding_service = _embedding_service
    vector_store = _vector_store
    session_manager = _session_manager
    llm_service = _llm_service

    # Service readiness check
    svc_err = _check_services()
    if svc_err:
        return svc_err

    session_id = request.sessionId
    question = request.question

    start_time = time.time()

    # --- Validate question ---
    if not question or not question.strip():
        return _err(400, "Question is required.", "EMPTY_MESSAGE", "Please type a question about your documents.")

    # --- Validate session ---
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        return _err(404, "Session not found.", "SESSION_NOT_FOUND", "Please upload documents first to create a session.")

    # --- Embed question ---
    question_embedding = embedding_service.embed(question)

    # --- Retrieve top-12 relevant chunks for richer context ---
    chunks = vector_store.query_top_k(session_id, question_embedding, k=12)

    # --- If very few chunks retrieved, supplement with all session chunks ---
    # This ensures the LLM has enough context for questions spanning the whole document
    if len(chunks) < 4:
        all_chunks = vector_store.get_all_chunks(session_id)
        # Merge: keep top-k first, add remaining up to 16 total
        seen_ids = {c.id for c in chunks}
        for chunk in all_chunks:
            if chunk.id not in seen_ids and len(chunks) < 16:
                chunks.append(chunk)
                seen_ids.add(chunk.id)

    # --- Build and call LLM ---
    doc_names = [doc.filename for doc in session.documents]
    system_prompt = get_system_prompt(doc_names)
    # Convert history models to plain dicts for the prompt builder
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    # Check semantic relevance — if all retrieved chunks have high distance,
    # the question is likely off-topic or not covered by the documents
    low_relevance = False
    if chunks:
        distances = [c.distance for c in chunks if c.distance is not None]
        if distances:
            avg_distance = sum(distances) / len(distances)
            # ChromaDB L2 distance: >1.5 means very low semantic similarity
            if avg_distance > 1.5:
                low_relevance = True
                logger.info(f"[chat] Low relevance detected: avg_distance={avg_distance:.2f}")

    # --- Fetch web context for richer chat responses ---
    from services import web_search
    web_sources = []
    try:
        web_context, raw_sources = await web_search.search_with_sources(f"greenwashing sustainability {question[:150]}")
        web_sources = raw_sources  # list of {title, url, snippet}
    except Exception:
        web_context = ""

    user_prompt = build_chat_prompt(question, chunks, history=history_dicts, low_relevance=low_relevance, simplify=request.simplify, web_context=web_context)

    try:
        raw = await llm_service.complete(system_prompt, user_prompt, max_tokens=6144, tier="quality")
        logger.info(f"[chat] raw LLM response: {len(raw)} chars, first 200: {raw[:200]!r}")
        raw = _strip_json_fences(raw)
        logger.info(f"[chat] after strip_json_fences, first 200: {raw[:200]!r}")

        import re
        # Only remove true control characters — do NOT escape \n or \t as that breaks JSON strings
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)

        # Fix escaped single quotes used as JSON keys (\'key\' -> "key")
        raw = re.sub(r"\\'([^']+)\\'", r'"\1"', raw)

        # Aggressive pre-parsing: find FIRST { and LAST } before attempting json.loads
        # This handles deepseek-v4-pro outputting prose before/after the JSON block
        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            raw = raw[brace_start:brace_end + 1]
        raw = raw.strip()
        logger.info(f"[chat] after brace extraction, first 200: {raw[:200]!r}")

        # Try to parse JSON, with fallback extraction
        data = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try cleaning trailing commas and retry
            cleaned = re.sub(r',\s*([}\]])', r'\1', raw)
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try fixing missing opening quotes on values (e.g. "impact": Unknowing... → "impact": "Unknowing...)
                # This handles LLM generating: "key": value without quotes around string values
                repaired = re.sub(
                    r'("(?:answer|evidence|risks|recommendation|quote|sourceDocument|documentType|risk|severity|impact|source|title|summary|nextSteps|confidence)")\s*:\s*(?!")([A-Z$\[][^\n,}]*)',
                    r'\1: "\2"',
                    cleaned,
                )
                try:
                    data = json.loads(repaired)
                    logger.info("[chat] JSON parse succeeded after missing-quote repair")
                except json.JSONDecodeError:
                    pass

        # If JSON parsing totally failed, return the raw text as the answer
        if data is None:
            logger.warning(f"[chat] JSON parse failed after all attempts. Raw first 500: {raw[:500]!r}")
            # Last resort: try to regex-extract the answer field from the raw JSON-like text
            answer_match = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', raw, re.DOTALL)
            if answer_match:
                extracted_answer = answer_match.group(1)
                # Unescape JSON string escapes
                extracted_answer = extracted_answer.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                logger.info(f"[chat] Regex-extracted answer from failed JSON: {len(extracted_answer)} chars")
                structured_response = StructuredAIResponse(
                    answer=extracted_answer,
                    evidence=[],
                    risks="",
                    recommendation="",
                )
            else:
                # If even the regex fails, strip any JSON wrapper characters and give the raw text
                fallback_answer = raw.strip()
                # Remove leading/trailing braces if the raw text looks like it's almost JSON
                if fallback_answer.startswith("{"):
                    fallback_answer = re.sub(r'^\{\s*', '', fallback_answer)
                if fallback_answer.endswith("}"):
                    fallback_answer = re.sub(r'\s*\}$', '', fallback_answer)
                # Remove JSON key prefixes
                fallback_answer = re.sub(r'^"answer"\s*:\s*"?', '', fallback_answer).strip()
                # Remove trailing evidence/risks/recommendation blocks
                fallback_answer = re.sub(r',?\s*"(evidence|risks|recommendation)":\s*[\[\{"][\s\S]*$', '', fallback_answer).strip()
                # Strip trailing quote if leftover
                if fallback_answer.endswith('"'):
                    fallback_answer = fallback_answer[:-1].strip()
                structured_response = StructuredAIResponse(
                    answer=fallback_answer if fallback_answer else raw.strip(),
                    evidence=[],
                    risks="",
                    recommendation="",
                )
        else:
            answer = data.get("answer", "")
            logger.info(f"[chat] Parsed OK. answer={len(answer)} chars, evidence={len(data.get('evidence', []))}")

            # Safety: if the answer field itself is a JSON string or starts with '{',
            # it means the model put structured data into the answer field — extract it cleanly.
            if isinstance(answer, dict):
                # Model returned answer as a dict object — flatten to string
                answer = answer.get("text", answer.get("content", answer.get("answer", str(answer))))
            elif isinstance(answer, str):
                stripped_ans = answer.strip()
                # If answer looks like a raw JSON object/array, the model likely echoed the
                # full response structure into the answer field — replace with a sensible fallback.
                if stripped_ans.startswith("{") and stripped_ans.endswith("}"):
                    try:
                        inner = json.loads(stripped_ans)
                        # Check if it's actually a full response object (has evidence/risks/recommendation)
                        # If so, extract the nested answer and also merge evidence if the outer data is empty.
                        if "answer" in inner and ("evidence" in inner or "risks" in inner):
                            nested_answer = inner.get("answer", "")
                            if isinstance(nested_answer, str) and len(nested_answer) > 10:
                                answer = nested_answer
                                # If outer response has no evidence, pull from nested
                                if not data.get("evidence") and inner.get("evidence"):
                                    data["evidence"] = inner["evidence"]
                                if not data.get("risks") and inner.get("risks"):
                                    data["risks"] = inner["risks"]
                                if not data.get("recommendation") and inner.get("recommendation"):
                                    data["recommendation"] = inner["recommendation"]
                            else:
                                answer = str(nested_answer) if nested_answer else stripped_ans
                        else:
                            # It's a JSON object but not a full response — extract text content
                            answer = (
                                inner.get("text")
                                or inner.get("content")
                                or inner.get("summary")
                                or inner.get("answer")
                                or stripped_ans  # keep as-is if no text field found
                            )
                        if not isinstance(answer, str):
                            answer = str(answer)
                    except json.JSONDecodeError:
                        pass  # Not actually JSON — keep as-is

            # Strip JSON key prefixes that the LLM sometimes leaves in the answer text
            # e.g. the answer starts with "*answer*: " or '"answer": "'
            import re as _re
            answer = _re.sub(r'^[\s"]*\*?answer\*?\s*[:=]\s*["\']?', '', answer, flags=re.IGNORECASE).strip()
            # Strip trailing quote if the above left one dangling
            if answer.endswith('"') and not answer.startswith('"'):
                answer = answer[:-1].strip()

            # Only strip truly dangling trailing JSON blobs (e.g. model appended evidence array to text).
            # Use a narrower pattern that matches only arrays/objects at the very end preceded by whitespace,
            # and only if the answer is long enough that stripping won't destroy meaningful content.
            if len(answer) > 100:
                # Strip trailing JSON arrays that got accidentally appended
                answer = _re.sub(r'\n\s*\[[\s\S]{20,}\]\s*$', '', answer).strip()
                answer = _re.sub(r'\n\s*\{[\s\S]{20,}\}\s*$', '', answer).strip()
                # Strip trailing JSON-like key-value pairs that leaked into the answer
                # e.g. answer ends with: , "evidence": [...], "risks": "..."
                answer = _re.sub(r',?\s*"(evidence|risks|recommendation)":\s*[\[\{"][\s\S]*$', '', answer).strip()
            # Parse structured response from JSON
            evidence_list = []
            for ev in data.get("evidence", []):
                # Truncate quote to 200 chars max
                quote = ev.get("quote", "")[:200]
                evidence_list.append(
                    Evidence(
                        quote=quote,
                        sourceDocument=ev.get("sourceDocument", ""),
                        documentType=ev.get("documentType", "pdf"),
                    )
                )

            # Coerce risks to string — LLM sometimes returns a list or dict
            raw_risks = data.get("risks", "")
            if isinstance(raw_risks, list):
                risk_parts = []
                for item in raw_risks:
                    if isinstance(item, str):
                        risk_parts.append(item)
                    elif isinstance(item, dict):
                        # Handle both {description: "..."} and {risk: "...", severity: "...", impact: "..."}
                        risk_text = item.get("description") or item.get("risk") or str(item)
                        severity = item.get("severity", "")
                        impact = item.get("impact", "")
                        if severity and risk_text != str(item):
                            risk_text = f"[{severity}] {risk_text}"
                        if impact:
                            risk_text += f" Impact: {impact}"
                        risk_parts.append(risk_text)
                    else:
                        risk_parts.append(str(item))
                risks_str = " | ".join(risk_parts)
            elif isinstance(raw_risks, dict):
                risks_str = raw_risks.get("description", str(raw_risks))
            else:
                risks_str = str(raw_risks) if raw_risks else ""

            # Coerce recommendation to string — same issue possible
            raw_rec = data.get("recommendation", "")
            if isinstance(raw_rec, dict):
                rec_str = raw_rec.get("summary", raw_rec.get("title", str(raw_rec)))
            elif isinstance(raw_rec, list):
                rec_str = " ".join(str(r) for r in raw_rec)
            else:
                rec_str = str(raw_rec) if raw_rec else ""

            structured_response = StructuredAIResponse(
                answer=answer,
                evidence=evidence_list,
                risks=risks_str,
                recommendation=rec_str,
            )

    except Exception as e:
        logger.error(f"Chat LLM error for session {session_id}: {e}", exc_info=True)
        # Don't expose internal API URLs or model IDs to end users
        err_str = str(e).lower()
        if "404" in err_str or "not found" in err_str:
            user_msg = "The AI model is temporarily unavailable. Please try again in a moment."
        elif "rate limit" in err_str or "429" in err_str:
            user_msg = "AI service is busy. Please wait a moment and try again."
        elif "timeout" in err_str:
            user_msg = "The AI took too long to respond. Please try a shorter question."
        else:
            user_msg = "The AI service encountered an error. Please try again."
        return _err(502, user_msg, "STREAM_FAILED", "If this persists, try refreshing the page or starting a new session.")

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Build source links from web search results
    from models.response import SourceLink
    source_links = [
        SourceLink(title=s.get("title", ""), url=s.get("url", ""), snippet=s.get("snippet", ""))
        for s in web_sources
        if s.get("url")
    ][:5]  # max 5 sources

    response = ChatResponse(
        messageId=str(uuid.uuid4()),
        role="assistant",
        structuredResponse=structured_response,
        processingTimeMs=elapsed_ms,
        sources=source_links,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        headers={"X-Processing-Time-Ms": str(elapsed_ms)},
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response as Server-Sent Events.
    Streams the answer token by token, then sends a final JSON event with
    evidence, risks, recommendation, and processingTimeMs.
    """
    embedding_service = _embedding_service
    vector_store = _vector_store
    session_manager = _session_manager
    llm_service = _llm_service

    # Service readiness check
    svc_err = _check_services()
    if svc_err:
        return svc_err

    session_id = request.sessionId
    question = request.question
    start_time = time.time()

    # --- Validate ---
    if not question or not question.strip():
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'code': 'EMPTY_MESSAGE', 'error': 'Question is required.', 'suggestion': 'Please type a question about your documents.'})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'code': 'SESSION_NOT_FOUND', 'error': 'Session not found.', 'suggestion': 'Please upload documents first to create a session.'})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    # --- Retrieve chunks ---
    question_embedding = embedding_service.embed(question)
    chunks = vector_store.query_top_k(session_id, question_embedding, k=12)
    if len(chunks) < 4:
        all_chunks = vector_store.get_all_chunks(session_id)
        seen_ids = {c.id for c in chunks}
        for chunk in all_chunks:
            if chunk.id not in seen_ids and len(chunks) < 16:
                chunks.append(chunk)
                seen_ids.add(chunk.id)

    doc_names = [doc.filename for doc in session.documents]
    system_prompt = get_system_prompt(doc_names)
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    # Check semantic relevance for streaming endpoint too
    low_relevance = False
    if chunks:
        distances = [c.distance for c in chunks if c.distance is not None]
        if distances:
            avg_distance = sum(distances) / len(distances)
            if avg_distance > 1.5:
                low_relevance = True
                logger.info(f"[chat/stream] Low relevance detected: avg_distance={avg_distance:.2f}")

    # --- Fetch web context for richer streaming responses ---
    from services import web_search
    try:
        web_context = await web_search.search(f"greenwashing sustainability {question[:150]}")
    except Exception:
        web_context = ""

    user_prompt = build_chat_prompt(question, chunks, history=history_dicts, low_relevance=low_relevance, simplify=request.simplify, web_context=web_context)

    async def generate():
        try:
            # Get full LLM response
            raw = await llm_service.complete(system_prompt, user_prompt, max_tokens=6144, tier="quality")
            logger.info(f"[chat/stream] raw LLM response: {len(raw)} chars, first 200: {raw[:200]!r}")
            raw = _strip_json_fences(raw)

            import re
            # Only remove true control characters — do NOT escape \n or \t as that breaks JSON strings
            raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)

            # Fix escaped single quotes used as JSON keys (\'key\' -> "key")
            raw = re.sub(r"\\'([^']+)\\'", r'"\1"', raw)

            # Aggressive pre-parsing: find FIRST { and LAST } before attempting json.loads
            # This handles deepseek-v4-pro outputting prose before/after the JSON block
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                raw = raw[brace_start:brace_end + 1]
            raw = raw.strip()
            logger.info(f"[chat/stream] after brace extraction, first 200: {raw[:200]!r}")

            # Robust JSON extraction — same logic as /chat endpoint
            data = None
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Try cleaning trailing commas and retry
                cleaned = re.sub(r',\s*([}\]])', r'\1', raw)
                try:
                    data = json.loads(cleaned)
                except json.JSONDecodeError:
                    # Try fixing missing opening quotes on values (e.g. "impact": Unknowing... → "impact": "Unknowing...)
                    repaired = re.sub(
                        r'("(?:answer|evidence|risks|recommendation|quote|sourceDocument|documentType|risk|severity|impact|source|title|summary|nextSteps|confidence)")\s*:\s*(?!")([A-Z$\[][^\n,}]*)',
                        r'\1: "\2"',
                        cleaned,
                    )
                    try:
                        data = json.loads(repaired)
                        logger.info("[chat/stream] JSON parse succeeded after missing-quote repair")
                    except json.JSONDecodeError:
                        logger.warning(f"[chat/stream] JSON parse failed after all attempts. Raw first 500: {raw[:500]!r}")

            # If JSON parsing totally failed, treat the raw text as the answer
            if data is None:
                # Last resort: try to regex-extract the answer field from the raw JSON-like text
                answer_match = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', raw, re.DOTALL)
                if answer_match:
                    extracted_answer = answer_match.group(1)
                    extracted_answer = extracted_answer.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                    answer = extracted_answer
                else:
                    # Strip JSON wrapper characters and give the raw text
                    fallback_answer = raw.strip()
                    if fallback_answer.startswith("{"):
                        fallback_answer = re.sub(r'^\{\s*', '', fallback_answer)
                    if fallback_answer.endswith("}"):
                        fallback_answer = re.sub(r'\s*\}$', '', fallback_answer)
                    fallback_answer = re.sub(r'^"answer"\s*:\s*"?', '', fallback_answer).strip()
                    fallback_answer = re.sub(r',?\s*"(evidence|risks|recommendation)":\s*[\[\{"][\s\S]*$', '', fallback_answer).strip()
                    if fallback_answer.endswith('"'):
                        fallback_answer = fallback_answer[:-1].strip()
                    answer = fallback_answer if fallback_answer else raw.strip()
                evidence_list = []
                risks_str = ""
                rec_str = ""
            else:
                answer = data.get("answer", "")
                # Safety: if the answer field is a dict or a stringified JSON object,
                # the model put structured data there — extract plain text.
                if isinstance(answer, dict):
                    answer = answer.get("text", answer.get("content", answer.get("answer", str(answer))))
                elif isinstance(answer, str):
                    stripped_ans = answer.strip()
                    if stripped_ans.startswith("{") and stripped_ans.endswith("}"):
                        try:
                            inner = json.loads(stripped_ans)
                            # Check if it's a full response object (has evidence/risks/recommendation)
                            if "answer" in inner and ("evidence" in inner or "risks" in inner):
                                nested_answer = inner.get("answer", "")
                                if isinstance(nested_answer, str) and len(nested_answer) > 10:
                                    answer = nested_answer
                                    # If outer response has no evidence, pull from nested
                                    if not data.get("evidence") and inner.get("evidence"):
                                        data["evidence"] = inner["evidence"]
                                    if not data.get("risks") and inner.get("risks"):
                                        data["risks"] = inner["risks"]
                                    if not data.get("recommendation") and inner.get("recommendation"):
                                        data["recommendation"] = inner["recommendation"]
                                else:
                                    answer = str(nested_answer) if nested_answer else stripped_ans
                            else:
                                answer = (
                                    inner.get("text")
                                    or inner.get("content")
                                    or inner.get("summary")
                                    or inner.get("answer")
                                    or stripped_ans
                                )
                            if not isinstance(answer, str):
                                answer = str(answer)
                        except json.JSONDecodeError:
                            pass

                # Strip JSON key prefixes that the LLM sometimes leaves in the answer text
                import re as _re
                answer = _re.sub(r'^[\s"]*\*?answer\*?\s*[:=]\s*["\']?', '', answer, flags=re.IGNORECASE).strip()
                if answer.endswith('"') and not answer.startswith('"'):
                    answer = answer[:-1].strip()

                # Only strip truly dangling trailing JSON blobs
                if len(answer) > 100:
                    answer = _re.sub(r'\n\s*\[[\s\S]{20,}\]\s*$', '', answer).strip()
                    answer = _re.sub(r'\n\s*\{[\s\S]{20,}\}\s*$', '', answer).strip()
                    # Strip trailing JSON-like key-value pairs that leaked into the answer
                    answer = _re.sub(r',?\s*"(evidence|risks|recommendation)":\s*[\[\{"][\s\S]*$', '', answer).strip()

                # Build evidence list
                evidence_list = []
                for ev in data.get("evidence", []):
                    quote = ev.get("quote", "")[:200]
                    evidence_list.append({
                        "quote": quote,
                        "sourceDocument": ev.get("sourceDocument", ""),
                        "documentType": ev.get("documentType", "pdf"),
                    })

                # Coerce risks
                raw_risks = data.get("risks", "")
                if isinstance(raw_risks, list):
                    risk_parts = []
                    for item in raw_risks:
                        if isinstance(item, str):
                            risk_parts.append(item)
                        elif isinstance(item, dict):
                            risk_text = item.get("description") or item.get("risk") or str(item)
                            severity = item.get("severity", "")
                            impact = item.get("impact", "")
                            if severity and risk_text != str(item):
                                risk_text = f"[{severity}] {risk_text}"
                            if impact:
                                risk_text += f" Impact: {impact}"
                            risk_parts.append(risk_text)
                        else:
                            risk_parts.append(str(item))
                    risks_str = " | ".join(risk_parts)
                elif isinstance(raw_risks, dict):
                    risks_str = raw_risks.get("description", str(raw_risks))
                else:
                    risks_str = str(raw_risks) if raw_risks else ""

                # Coerce recommendation
                raw_rec = data.get("recommendation", "")
                if isinstance(raw_rec, dict):
                    rec_str = raw_rec.get("summary", raw_rec.get("title", str(raw_rec)))
                elif isinstance(raw_rec, list):
                    rec_str = " ".join(str(r) for r in raw_rec)
                else:
                    rec_str = str(raw_rec) if raw_rec else ""

            # Stream answer word by word
            words = answer.split(" ")
            for i, word in enumerate(words):
                chunk_text = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'text': chunk_text})}\n\n"
                await asyncio.sleep(0.008)  # ~125 words/sec — fast but readable

            elapsed_ms = int((time.time() - start_time) * 1000)
            message_id = str(uuid.uuid4())

            # Final event with full structured data
            final = {
                "type": "done",
                "messageId": message_id,
                "role": "assistant",
                "structuredResponse": {
                    "answer": answer,
                    "evidence": evidence_list,
                    "risks": risks_str,
                    "recommendation": rec_str,
                },
                "processingTimeMs": elapsed_ms,
            }
            yield f"data: {json.dumps(final)}\n\n"

        except Exception as e:
            logger.error(f"Stream error for session {session_id}: {e}", exc_info=True)
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str:
                user_msg = "The AI model is temporarily unavailable. Please try again in a moment."
            elif "rate limit" in err_str or "429" in err_str:
                user_msg = "AI service is busy. Please wait a moment and try again."
            elif "timeout" in err_str:
                user_msg = "The AI took too long to respond. Please try a shorter question."
            else:
                user_msg = "The AI service encountered an error. Please try again."
            yield f"data: {json.dumps({'type': 'error', 'code': 'STREAM_FAILED', 'error': user_msg, 'suggestion': 'If this persists, try refreshing the page or starting a new session.'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )


@router.post("/chat/vision")
async def chat_vision(
    image: UploadFile = File(...),
    sessionId: str = Form(""),
    question: str = Form(""),
):
    """
    Analyze an uploaded image using the vision model.

    Accepts multipart form: image file + optional sessionId and question.
    Returns a ChatResponse with the vision model's analysis.
    """
    import base64

    llm_service = _llm_service

    # Service readiness check
    svc_err = _check_services()
    if svc_err:
        return svc_err

    start_time = time.time()

    # --- Validate image MIME type ---
    content_type = (image.content_type or "").split(";")[0].strip().lower()
    allowed_image_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if content_type not in allowed_image_types:
        return _err(
            400,
            f"Unsupported image type: {content_type}. Accepted: PNG, JPEG, WebP.",
            "INVALID_FILE_TYPE",
            "Please upload a PNG, JPEG, or WebP image.",
        )

    # --- Read and validate size (max 10 MB) ---
    image_bytes = await image.read()
    max_image_size = 10 * 1024 * 1024  # 10 MB
    if len(image_bytes) > max_image_size:
        return _err(
            400,
            "Image exceeds 10 MB limit.",
            "FILE_TOO_LARGE",
            "Please upload an image smaller than 10 MB.",
        )

    # --- Check if vision model is configured ---
    if not llm_service._model_vision:
        # Graceful fallback — don't crash, return helpful message
        elapsed_ms = int((time.time() - start_time) * 1000)
        structured_response = StructuredAIResponse(
            answer=(
                "Vision analysis is not currently available. "
                "The FIREWORKS_MODEL_VISION environment variable is not configured. "
                "Please set it to a vision-capable model to enable image analysis."
            ),
            evidence=[],
            risks="Vision model not configured — image analysis disabled.",
            recommendation="Configure FIREWORKS_MODEL_VISION in your environment to enable this feature.",
        )
        response = ChatResponse(
            messageId=str(uuid.uuid4()),
            role="assistant",
            structuredResponse=structured_response,
            processingTimeMs=elapsed_ms,
        )
        return JSONResponse(content=response.model_dump(mode="json"))

    # --- Base64 encode image ---
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # --- Build prompt ---
    user_text = question.strip() if question and question.strip() else (
        "Analyze this image for sustainability or environmental claims. "
        "Identify any greenwashing indicators, marketing claims, certifications, "
        "or environmental messaging. Assess credibility and flag concerns."
    )

    system_prompt = (
        "You are GreenLens AI — a sustainability claims analyst. "
        "Analyze images for greenwashing, misleading environmental claims, "
        "packaging language, certification logos, and marketing tactics. "
        "Be direct and specific in your findings."
    )

    try:
        raw = await llm_service.complete_vision(
            system_prompt=system_prompt,
            user_text=user_text,
            image_base64=image_base64,
            image_mime=content_type,
            max_tokens=800,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        structured_response = StructuredAIResponse(
            answer=raw,
            evidence=[],
            risks="",
            recommendation="",
        )

        response = ChatResponse(
            messageId=str(uuid.uuid4()),
            role="assistant",
            structuredResponse=structured_response,
            processingTimeMs=elapsed_ms,
        )
        return JSONResponse(
            content=response.model_dump(mode="json"),
            headers={"X-Processing-Time-Ms": str(elapsed_ms)},
        )

    except Exception as e:
        logger.error(f"[chat/vision] Error: {e}", exc_info=True)
        return _err(
            502,
            f"Vision analysis failed: {type(e).__name__}: {str(e)[:120]}",
            "STREAM_FAILED",
            "The vision AI service encountered an error. Please try again.",
        )
