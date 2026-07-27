"""
Feedback API routes -- user corrections and feedback-to-training pipeline.
"""

import logging
from typing import List

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models.feedback import CorrectionResult, UserCorrection
from services.feedback_learning import FeedbackLearningService
from services.training_pipeline import TrainingPipelineService

logger = logging.getLogger(__name__)

router = APIRouter()

_training_pipeline = TrainingPipelineService()
_feedback_service = FeedbackLearningService(training_pipeline=_training_pipeline)


class PromoteCorrectionRequest(BaseModel):
    correction_ids: List[str]


@router.post("/feedback/corrections", response_model=CorrectionResult)
async def submit_correction(correction: UserCorrection):
    try:
        result = await _feedback_service.submit_correction(correction)
        return JSONResponse(status_code=201, content=result.model_dump(mode="json"))
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to submit correction: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to submit correction.", "code": "INTERNAL_ERROR"})


@router.get("/feedback/pending", response_model=list[UserCorrection])
async def get_pending_corrections():
    try:
        pending = await _feedback_service.get_pending_corrections()
        return JSONResponse(content=[c.model_dump(mode="json") for c in pending])
    except Exception as e:
        logger.error(f"Failed to get pending corrections: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to retrieve pending corrections.", "code": "INTERNAL_ERROR"})


@router.post("/feedback/promote")
async def promote_corrections(body: PromoteCorrectionRequest):
    try:
        all_corrections = await _feedback_service._read_all_corrections()
        selected = [c for c in all_corrections if c.id in body.correction_ids]
        if not selected:
            return JSONResponse(status_code=404, content={"error": "No corrections found for the given IDs.", "code": "NOT_FOUND"})
        result = await _feedback_service.promote_to_dataset(selected)
        return JSONResponse(content={"status": "promoted", "training_example_id": result.id, "promoted_count": len(selected)})
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to promote corrections: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to promote corrections.", "code": "INTERNAL_ERROR"})
