"""FeedbackLearningService -- manages user corrections and feedback-to-training pipeline."""
import json
import logging
import os
from uuid import uuid4

from models.feedback import CorrectionResult, UserCorrection, ConsensusResult, ConflictCheckResult
from models.training import (
    ChatMessage, ExampleSource, GreenwashVerdict, SeverityLevel, TrainingExample,
)

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "feedback")


class FeedbackLearningService:
    def __init__(self, data_dir: str | None = None, training_pipeline=None):
        self.data_dir = data_dir or _DATA_DIR
        self.corrections_file = os.path.join(self.data_dir, "corrections.jsonl")
        self.training_pipeline = training_pipeline
        os.makedirs(self.data_dir, exist_ok=True)

    async def submit_correction(self, correction: UserCorrection) -> CorrectionResult:
        if not correction.id:
            correction.id = str(uuid4())
        await self._store_correction(correction)
        consensus = await self.check_consensus(correction.error_type, correction.original_input)
        if consensus.has_consensus:
            return CorrectionResult(correction_id=correction.id, status="consensus_reached", consensus_count=consensus.correction_count)
        return CorrectionResult(correction_id=correction.id, status="logged", consensus_count=consensus.correction_count)

    async def check_consensus(self, error_type: str, claim_text: str) -> ConsensusResult:
        all_corrections = await self._read_all_corrections()
        matching = [c for c in all_corrections if c.error_type == error_type and c.original_input == claim_text]
        unique_users = set(c.user_id for c in matching)
        return ConsensusResult(
            has_consensus=len(unique_users) >= 3,
            correction_count=len(unique_users),
            corrections=matching,
        )

    async def promote_to_dataset(self, corrections: list[UserCorrection]) -> TrainingExample:
        if not corrections:
            raise ValueError("No corrections to promote")
        first = corrections[0]
        messages = [
            ChatMessage(role="system", content="Classify the following sustainability claim."),
            ChatMessage(role="user", content=first.original_input),
            ChatMessage(role="assistant", content=first.user_correction),
        ]
        verdict = GreenwashVerdict.MISLEADING
        if first.correction_type == "false_positive":
            verdict = GreenwashVerdict.SUBSTANTIATED
        example = TrainingExample(
            messages=messages, label=verdict, severity=SeverityLevel.MEDIUM,
            sector="general", company="unknown", source=ExampleSource.FEEDBACK,
        )
        if self.training_pipeline:
            return await self.training_pipeline.add_example(example)
        return example

    async def check_conflict(self, correction: UserCorrection) -> ConflictCheckResult:
        """Check if correction contradicts an expert-labeled training example for the same claim."""
        if not self.training_pipeline:
            return ConflictCheckResult(has_conflict=False)
        expert_examples = await self.training_pipeline.get_examples(source="expert")
        for ex in expert_examples:
            # Find expert examples matching the same original input (claim text)
            user_msg = next((m.content for m in ex.messages if m.role == "user"), None)
            if user_msg and user_msg == correction.original_input:
                # Determine what the user's correction implies about the verdict
                user_verdict = GreenwashVerdict.SUBSTANTIATED if correction.correction_type == "false_positive" else GreenwashVerdict.MISLEADING
                if user_verdict != ex.label:
                    return ConflictCheckResult(
                        has_conflict=True,
                        conflicting_example_id=ex.id,
                        conflicting_label=ex.label.value if isinstance(ex.label, GreenwashVerdict) else str(ex.label),
                        requires_expert_review=True,
                    )
        return ConflictCheckResult(has_conflict=False)

    async def get_pending_corrections(self) -> list[UserCorrection]:
        all_corrections = await self._read_all_corrections()
        pending = []
        seen_claims: dict[str, list[str]] = {}
        for c in all_corrections:
            key = f"{c.error_type}:{c.original_input}"
            if key not in seen_claims:
                seen_claims[key] = []
            seen_claims[key].append(c.user_id)
        for c in all_corrections:
            key = f"{c.error_type}:{c.original_input}"
            unique_users = set(seen_claims.get(key, []))
            if len(unique_users) < 3:
                pending.append(c)
        return pending

    async def _store_correction(self, correction: UserCorrection) -> None:
        data = correction.model_dump(mode="json")
        with open(self.corrections_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    async def _read_all_corrections(self) -> list[UserCorrection]:
        corrections: list[UserCorrection] = []
        if not os.path.exists(self.corrections_file):
            return corrections
        with open(self.corrections_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    corrections.append(UserCorrection.model_validate(json.loads(line)))
                except Exception:
                    pass
        return corrections
