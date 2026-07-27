"""
Prompts API routes -- manage prompt versions, evaluation, promotion, and rollback.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models.prompts import PromptEvaluationResult, PromptVersion

logger = logging.getLogger(__name__)

router = APIRouter()

_prompt_optimizer = None


def _check_services():
    if _prompt_optimizer is None:
        return JSONResponse(
            status_code=503,
            content={"error": "Service is starting up. Please try again in a moment.", "code": "SERVICE_UNAVAILABLE"},
        )
    return None


class RegisterVersionRequest(BaseModel):
    prompt_name: str
    content: str
    version: str


class EvaluateCandidateRequest(BaseModel):
    prompt_name: str
    candidate_version: str


class PromoteRequest(BaseModel):
    prompt_name: str
    version: str


class RollbackRequest(BaseModel):
    prompt_name: str


@router.post("/prompts/versions", response_model=PromptVersion)
async def register_prompt_version(body: RegisterVersionRequest):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        version = await _prompt_optimizer.register_version(
            prompt_name=body.prompt_name, content=body.content, version=body.version,
        )
        return JSONResponse(status_code=201, content=version.model_dump(mode="json"))
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to register prompt version: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to register prompt version.", "code": "INTERNAL_ERROR"})


@router.post("/prompts/evaluate", response_model=PromptEvaluationResult)
async def evaluate_prompt(body: EvaluateCandidateRequest):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        result = await _prompt_optimizer.evaluate_candidate(
            prompt_name=body.prompt_name, candidate_version=body.candidate_version,
        )
        return JSONResponse(content=result.model_dump(mode="json"))
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to evaluate prompt: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Evaluation failed: {str(e)[:200]}", "code": "EVALUATION_ERROR"})


@router.post("/prompts/promote")
async def promote_prompt(body: PromoteRequest):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        success = await _prompt_optimizer.promote(prompt_name=body.prompt_name, version=body.version)
        if success:
            return JSONResponse(content={"status": "promoted", "version": body.version})
        else:
            return JSONResponse(status_code=400, content={"error": "Promotion failed: candidate does not beat production on all categories.", "code": "PROMOTION_REJECTED"})
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to promote prompt: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to promote prompt.", "code": "INTERNAL_ERROR"})


@router.post("/prompts/rollback")
async def rollback_prompt(body: RollbackRequest):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        previous_version = await _prompt_optimizer.rollback(prompt_name=body.prompt_name)
        return JSONResponse(content={"status": "rolled_back", "active_version": previous_version})
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to rollback prompt: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to rollback prompt.", "code": "INTERNAL_ERROR"})
