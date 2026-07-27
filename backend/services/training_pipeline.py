"""
TrainingPipelineService -- curates, validates, and stores labeled greenwashing
training examples as JSONL files.
"""
import json
import logging
import os
from uuid import uuid4

from models.training import (
    ChatMessage,
    DatasetStats,
    ExampleSource,
    GreenwashVerdict,
    TrainingExample,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "training")


class TrainingPipelineService:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or _DATA_DIR
        self.examples_file = os.path.join(self.data_dir, "examples.jsonl")
        os.makedirs(self.data_dir, exist_ok=True)

    async def validate_schema(self, example: TrainingExample) -> ValidationResult:
        errors: list[str] = []
        if len(example.messages) < 3:
            errors.append("messages: must contain at least 3 messages (system, user, assistant)")
        if len(example.messages) >= 3:
            roles = [msg.role for msg in example.messages]
            if "system" not in roles:
                errors.append("messages: must contain at least one message with role 'system'")
            if "user" not in roles:
                errors.append("messages: must contain at least one message with role 'user'")
            if "assistant" not in roles:
                errors.append("messages: must contain at least one message with role 'assistant'")
        valid_labels = {v.value for v in GreenwashVerdict}
        if example.label not in valid_labels and example.label not in GreenwashVerdict:
            errors.append(f"label: must be one of {sorted(valid_labels)}")
        if not example.sector or not example.sector.strip():
            errors.append("sector: must be a non-empty string")
        if not example.company or not example.company.strip():
            errors.append("company: must be a non-empty string")
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def add_example(self, example: TrainingExample) -> TrainingExample:
        validation = await self.validate_schema(example)
        if not validation.valid:
            raise ValueError(f"Invalid training example: {'; '.join(validation.errors)}")
        if not example.id:
            example.id = str(uuid4())
        example_data = example.model_dump(mode="json")
        with open(self.examples_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(example_data) + "\n")
        logger.info(f"Added training example {example.id}")
        return example

    async def get_dataset_stats(self) -> DatasetStats:
        examples = await self._read_all_examples()
        by_label: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_sector: dict[str, int] = {}
        by_source: dict[str, int] = {}
        for ex in examples:
            lk = ex.label.value if isinstance(ex.label, GreenwashVerdict) else str(ex.label)
            by_label[lk] = by_label.get(lk, 0) + 1
            sk = ex.severity.value if hasattr(ex.severity, "value") else str(ex.severity)
            by_severity[sk] = by_severity.get(sk, 0) + 1
            by_sector[ex.sector] = by_sector.get(ex.sector, 0) + 1
            src = ex.source.value if isinstance(ex.source, ExampleSource) else str(ex.source)
            by_source[src] = by_source.get(src, 0) + 1
        total = len(examples)
        return DatasetStats(
            total_examples=total, by_label=by_label, by_severity=by_severity,
            by_sector=by_sector, by_source=by_source,
            evaluation_ready=total >= 30, finetune_ready=total >= 200,
        )

    async def get_examples(self, label=None, sector=None, source=None, limit=50):
        examples = await self._read_all_examples()
        if label is not None:
            examples = [e for e in examples if (e.label.value if isinstance(e.label, GreenwashVerdict) else str(e.label)) == label]
        if sector is not None:
            examples = [e for e in examples if e.sector == sector]
        if source is not None:
            examples = [e for e in examples if (e.source.value if isinstance(e.source, ExampleSource) else str(e.source)) == source]
        return examples[:limit]

    async def is_evaluation_ready(self) -> bool:
        return len(await self._read_all_examples()) >= 30

    async def is_finetune_ready(self) -> bool:
        return len(await self._read_all_examples()) >= 200

    async def _read_all_examples(self) -> list[TrainingExample]:
        examples: list[TrainingExample] = []
        if not os.path.exists(self.examples_file):
            return examples
        with open(self.examples_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    examples.append(TrainingExample.model_validate(json.loads(line)))
                except Exception:
                    pass
        return examples
