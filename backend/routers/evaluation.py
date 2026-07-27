"""
Evaluation API routes -- run evaluation suites and compare prompts.
"""

import glob
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models.evaluation import EvaluationReport, PromptComparisonReport

logger = logging.getLogger(__name__)

router = APIRouter()

_evaluation_framework = None


def _check_services():
    if _evaluation_framework is None:
        return JSONResponse(
            status_code=503,
            content={"error": "Service is starting up. Please try again in a moment.", "code": "SERVICE_UNAVAILABLE"},
        )
    return None


class RunEvaluationRequest(BaseModel):
    prompt_version: Optional[str] = None
    max_examples: int = 50


class ComparePromptsRequest(BaseModel):
    prompt_a: str
    prompt_b: str


@router.post("/evaluation/run", response_model=EvaluationReport)
async def run_evaluation(body: RunEvaluationRequest):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        report = await _evaluation_framework.run_evaluation(
            prompt_version=body.prompt_version,
            max_examples=body.max_examples,
        )
        return JSONResponse(content=report.model_dump(mode="json"))
    except Exception as e:
        logger.error(f"Evaluation run failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Evaluation failed: {str(e)[:200]}", "code": "EVALUATION_ERROR"})


@router.post("/evaluation/compare", response_model=PromptComparisonReport)
async def compare_prompts(body: ComparePromptsRequest):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        report = await _evaluation_framework.compare_prompts(prompt_a=body.prompt_a, prompt_b=body.prompt_b)
        return JSONResponse(content=report.model_dump(mode="json"))
    except Exception as e:
        logger.error(f"Prompt comparison failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Comparison failed: {str(e)[:200]}", "code": "COMPARISON_ERROR"})


@router.get("/evaluation/reports", response_model=list[EvaluationReport])
async def list_evaluation_reports(
    limit: int = Query(20, ge=1, le=100, description="Maximum reports to return"),
):
    svc_err = _check_services()
    if svc_err:
        return svc_err
    try:
        reports_dir = _evaluation_framework.data_dir
        pattern = os.path.join(reports_dir, "*.json")
        report_files = glob.glob(pattern)
        reports: list[dict] = []
        for filepath in report_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    reports.append(data)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Skipping malformed report file {filepath}: {e}")
        reports.sort(key=lambda r: r.get("run_at", ""), reverse=True)
        return JSONResponse(content=reports[:limit])
    except Exception as e:
        logger.error(f"Failed to list evaluation reports: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to retrieve reports.", "code": "INTERNAL_ERROR"})
