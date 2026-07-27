"""
Integration test: end-to-end flow for training pipeline and feedback learning.

Covers:
- Adding training examples
- Checking evaluation/finetune readiness
- Dataset stats and filtered queries
- Feedback corrections reaching consensus
- Promoting feedback to training dataset
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.training import (
    ChatMessage,
    ExampleSource,
    GreenwashVerdict,
    SeverityLevel,
    TrainingExample,
)
from models.feedback import UserCorrection
from services.training_pipeline import TrainingPipelineService
from services.feedback_learning import FeedbackLearningService


def _make_example(label, severity, sector, company):
    """Helper to build a valid TrainingExample."""
    return TrainingExample(
        messages=[
            ChatMessage(role="system", content="Classify the sustainability claim."),
            ChatMessage(role="user", content=f"Claim from {company} in {sector} sector."),
            ChatMessage(role="assistant", content=f"Verdict: {label.value}"),
        ],
        label=label,
        severity=severity,
        sector=sector,
        company=company,
        source=ExampleSource.EXPERT,
    )


_LABELS = list(GreenwashVerdict)
_SEVERITIES = list(SeverityLevel)
_SECTORS = ["energy", "fashion", "food", "technology", "automotive"]


def _generate_examples(count=30):
    """Generate a diverse set of training examples."""
    examples = []
    for i in range(count):
        label = _LABELS[i % len(_LABELS)]
        severity = _SEVERITIES[i % len(_SEVERITIES)]
        sector = _SECTORS[i % len(_SECTORS)]
        company = f"Company_{i}"
        examples.append(_make_example(label, severity, sector, company))
    return examples


async def test_end_to_end_training_and_feedback(tmp_path):
    """
    Full integration flow:
    1. Add 30 examples -> evaluation ready, finetune not ready
    2. Verify stats and filtered queries
    3. Submit corrections -> consensus -> promote
    4. Verify promoted example with source=feedback and total=31
    """
    training_service = TrainingPipelineService(data_dir=str(tmp_path / "training"))
    feedback_service = FeedbackLearningService(
        data_dir=str(tmp_path / "feedback"),
        training_pipeline=training_service,
    )

    # --- Step 1: Add 30 valid training examples ---
    examples = _generate_examples(30)
    for ex in examples:
        await training_service.add_example(ex)

    # --- Step 2: Verify readiness flags ---
    assert await training_service.is_evaluation_ready() is True
    assert await training_service.is_finetune_ready() is False  # need 200

    # --- Step 3: Verify dataset stats ---
    stats = await training_service.get_dataset_stats()
    assert stats.total_examples == 30
    assert stats.evaluation_ready is True
    assert stats.finetune_ready is False

    # Verify distribution across labels
    for label in GreenwashVerdict:
        assert label.value in stats.by_label

    # Verify distribution across severities
    for sev in SeverityLevel:
        assert sev.value in stats.by_severity

    # Verify distribution across sectors
    for sector in _SECTORS:
        assert sector in stats.by_sector

    # All examples are expert-sourced
    assert stats.by_source.get("expert", 0) == 30

    # --- Step 4: Verify filtered queries ---
    energy_examples = await training_service.get_examples(sector="energy")
    assert len(energy_examples) > 0
    assert all(e.sector == "energy" for e in energy_examples)

    misleading_examples = await training_service.get_examples(label="MISLEADING")
    assert len(misleading_examples) > 0
    assert all(
        (e.label.value if isinstance(e.label, GreenwashVerdict) else e.label) == "MISLEADING"
        for e in misleading_examples
    )

    # --- Step 5: Submit 3 corrections from different users for same claim ---
    claim_text = "Our products are 100% eco-friendly"
    error_type = "false_negative"

    for i in range(3):
        correction = UserCorrection(
            session_id="session_integration_test",
            user_id=f"user_{i}",
            original_input=claim_text,
            ai_output="SUBSTANTIATED",
            correction_type="false_negative",
            user_correction="This claim is vague and unverifiable.",
            error_type=error_type,
        )
        result = await feedback_service.submit_correction(correction)

    # The third correction should trigger consensus
    assert result.status == "consensus_reached"
    assert result.consensus_count >= 3

    # --- Step 6: Verify consensus independently ---
    consensus = await feedback_service.check_consensus(error_type, claim_text)
    assert consensus.has_consensus is True
    assert consensus.correction_count >= 3

    # --- Step 7: Promote corrections to training dataset ---
    promoted = await feedback_service.promote_to_dataset(consensus.corrections)
    assert promoted.source == ExampleSource.FEEDBACK

    # --- Step 8: Verify total examples is now 31 ---
    final_stats = await training_service.get_dataset_stats()
    assert final_stats.total_examples == 31

    # Verify the promoted example appears in feedback-sourced queries
    feedback_examples = await training_service.get_examples(source="feedback")
    assert len(feedback_examples) == 1
    assert feedback_examples[0].source == ExampleSource.FEEDBACK