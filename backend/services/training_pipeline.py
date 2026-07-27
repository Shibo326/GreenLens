"""
TrainingPipelineService — curates, validates, and stores labeled greenwashing
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

# Default path for training examples JSONL file
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "training")
_EXAMPLES_FILE = os.path.join(_DATA_DIR, "examples.jsonl")


class TrainingPipelineService:
    """
    Responsible for curating, validating, and storing labeled greenwashing
    training examples in JSONL format.
    """

    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or _DATA_DIR
        self.examples_file = os.path.join(self.data_dir, "examples.jsonl")
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"TrainingPipelineService initialized — data dir: {self.data_dir}")

    async def validate_schema(self, example: TrainingExample) -> ValidationResult:
        """
        Validate example against Fireworks AI chat-completion format.

        Checks:
        - messages has >= 3 items with system/user/assistant roles
        - label is a valid GreenwashVerdict
        - sector and company are non-empty strings
        """
        errors: list[str] = []

        # Validate messages length
        if len(example.messages) < 3:
            errors.append("messages: must contain at least 3 messages (system, user, assistant)")

        # Validate role presence
        if len(example.messages) >= 3:
            roles = [msg.role for msg in example.messages]
            if "system" not in roles:
                errors.append("messages: must contain at least one message with role 'system'")
            if "user" not in roles:
                errors.append("messages: must contain at least one message with role 'user'")
            if "assistant" not in roles:
                errors.append("messages: must contain at least one message with role 'assistant'")

        # Validate label is a valid GreenwashVerdict
        valid_labels = {v.value for v in GreenwashVerdict}
        if example.label not in valid_labels and example.label not in GreenwashVerdict:
            errors.append(f"label: must be one of {sorted(valid_labels)}")

        # Validate sector is non-empty
        if not example.sector or not example.sector.strip():
            errors.append("sector: must be a non-empty string")

        # Validate company is non-empty
        if not example.company or not example.company.strip():
            errors.append("company: must be a non-empty string")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def add_example(self, example: TrainingExample) -> TrainingExample:
        """
        Validate and store a new training example.

        - Validates the example schema
        - Generates a UUID id if empty
        - Appends to the JSONL file
        - Returns the stored example
        """
        # Validate first
        validation = await self.validate_schema(example)
        if not validation.valid:
            raise ValueError(f"Invalid training example: {'; '.join(validation.errors)}")

        # Generate ID if not provided
        if not example.id:
            example.id = str(uuid4())

        # Serialize and append to JSONL
        example_data = example.model_dump(mode="json")
        # Convert datetime to ISO string for JSON serialization
        if "created_at" in example_data and hasattr(example_data["created_at"], "isoformat"):
            example_data["created_at"] = example_data["created_at"].isoformat()

        with open(self.examples_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(example_data) + "\n")

        logger.info(f"Added training example {example.id} (label={example.label.value}, sector={example.sector})")
        return example

    async def get_dataset_stats(self) -> DatasetStats:
        """
        Read all examples and compute counts by label, severity, sector, source.
        """
        examples = await self._read_all_examples()

        by_label: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_sector: dict[str, int] = {}
        by_source: dict[str, int] = {}

        for ex in examples:
            # Count by label
            label_key = ex.label.value if isinstance(ex.label, GreenwashVerdict) else str(ex.label)
            by_label[label_key] = by_label.get(label_key, 0) + 1

            # Count by severity
            severity_key = ex.severity.value if hasattr(ex.severity, "value") else str(ex.severity)
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1

            # Count by sector
            by_sector[ex.sector] = by_sector.get(ex.sector, 0) + 1

            # Count by source
            source_key = ex.source.value if isinstance(ex.source, ExampleSource) else str(ex.source)
            by_source[source_key] = by_source.get(source_key, 0) + 1

        total = len(examples)

        return DatasetStats(
            total_examples=total,
            by_label=by_label,
            by_severity=by_severity,
            by_sector=by_sector,
            by_source=by_source,
            evaluation_ready=total >= 30,
            finetune_ready=total >= 200,
        )

    async def get_examples(
        self,
        label: str | None = None,
        sector: str | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> list[TrainingExample]:
        """
        Query examples with optional filters (label, sector, source, limit).
        """
        examples = await self._read_all_examples()

        # Apply filters
        if label is not None:
            examples = [
                ex for ex in examples
                if (ex.label.value if isinstance(ex.label, GreenwashVerdict) else str(ex.label)) == label
            ]

        if sector is not None:
            examples = [ex for ex in examples if ex.sector == sector]

        if source is not None:
            examples = [
                ex for ex in examples
                if (ex.source.value if isinstance(ex.source, ExampleSource) else str(ex.source)) == source
            ]

        # Apply limit
        return examples[:limit]

    async def is_evaluation_ready(self) -> bool:
        """True if total_examples >= 30."""
        examples = await self._read_all_examples()
        return len(examples) >= 30

    async def is_finetune_ready(self) -> bool:
        """True if total_examples >= 200."""
        examples = await self._read_all_examples()
        return len(examples) >= 200

    async def _read_all_examples(self) -> list[TrainingExample]:
        """Read all training examples from the JSONL file."""
        examples: list[TrainingExample] = []

        if not os.path.exists(self.examples_file):
            return examples

        with open(self.examples_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    examples.append(TrainingExample.model_validate(data))
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Skipping malformed line {line_num} in {self.examples_file}: {e}")

        return examples
