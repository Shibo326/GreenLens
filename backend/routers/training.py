"""
Training API routes -- manage labeled greenwashing training examples.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from models.training import DatasetStats, TrainingExample
from services.training_pipeline import TrainingPipelineService

logger = logging.getLogger(__name__)

router = APIRouter()

_training_pipeline = TrainingPipelineService()


@router.post("/training/examples", response_model=TrainingExample)
async def add_training_example(example: TrainingExample):
    try:
        result = await _training_pipeline.add_example(example)
        return JSONResponse(status_code=201, content=result.model_dump(mode="json"))
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.error(f"Failed to add training example: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to add training example.", "code": "INTERNAL_ERROR"})


@router.get("/training/stats", response_model=DatasetStats)
async def get_training_stats():
    try:
        stats = await _training_pipeline.get_dataset_stats()
        return JSONResponse(content=stats.model_dump(mode="json"))
    except Exception as e:
        logger.error(f"Failed to get dataset stats: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to retrieve dataset stats.", "code": "INTERNAL_ERROR"})


@router.get("/training/examples", response_model=list[TrainingExample])
async def list_training_examples(
    label: Optional[str] = Query(None, description="Filter by greenwash verdict label"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    source: Optional[str] = Query(None, description="Filter by source (expert or feedback)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of examples to return"),
):
    try:
        examples = await _training_pipeline.get_examples(label=label, sector=sector, source=source, limit=limit)
        return JSONResponse(content=[ex.model_dump(mode="json") for ex in examples])
    except Exception as e:
        logger.error(f"Failed to list training examples: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to retrieve examples.", "code": "INTERNAL_ERROR"})
