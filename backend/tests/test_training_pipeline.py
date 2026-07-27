"""
Unit tests for TrainingPipelineService — validates Properties 1, 2, and 3.

Property 1: Training example validation correctness
Property 2: Training example storage round-trip
Property 3: Dataset readiness thresholds
"""

import pytest

from models.training import (
    ChatMessage,
    ExampleSource,
    GreenwashVerdict,
    SeverityLevel,
    TrainingExample,
)
from services.training_pipeline import TrainingPipelineService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_messages() -> list[ChatMessage]:
    """Return a minimal valid messages list (system, user, assistant)."""
    return [
        ChatMessage(role="system", content="You are a greenwashing detection assistant."),
        ChatMessage(role="user", content="Evaluate this claim: 'Our products are 100% eco-friendly'."),
        ChatMessage(role="assistant", content="This claim is vague and unsubstantiated."),
    ]


def _make_valid_example(**overrides) -> TrainingExample:
    """Create a valid TrainingExample with optional field overrides."""
    defaults = dict(
        messages=_valid_messages(),
        label=GreenwashVerdict.MISLEADING,
        severity=SeverityLevel.HIGH,
        sector="Energy",
        company="TestCorp",
        source=ExampleSource.EXPERT,
    )
    defaults.update(overrides)
    return TrainingExample(**defaults)


# ---------------------------------------------------------------------------
# Property 1: Validation correctness
# ---------------------------------------------------------------------------


class TestValidationAcceptsValid:
    """validate_schema accepts well-formed examples."""

    async def test_minimal_valid_example(self, tmp_path):
        """Accepts example with exactly 3 messages (system/user/assistant)."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        example = _make_valid_example()
        result = await svc.validate_schema(example)
        assert result.valid is True
        assert result.errors == []

    async def test_all_label_values_accepted(self, tmp_path):
        """Accepts every valid GreenwashVerdict label."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for verdict in GreenwashVerdict:
            example = _make_valid_example(label=verdict)
            result = await svc.validate_schema(example)
            assert result.valid is True, f"Label {verdict.value} should be accepted"

    async def test_extra_messages_accepted(self, tmp_path):
        """Accepts messages list with more than 3 messages."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        msgs = _valid_messages() + [
            ChatMessage(role="user", content="Can you elaborate?"),
            ChatMessage(role="assistant", content="Sure, here is more detail."),
        ]
        example = _make_valid_example(messages=msgs)
        result = await svc.validate_schema(example)
        assert result.valid is True

    async def test_all_severity_levels_accepted(self, tmp_path):
        """Accepts every valid SeverityLevel."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for severity in SeverityLevel:
            example = _make_valid_example(severity=severity)
            result = await svc.validate_schema(example)
            assert result.valid is True


class TestValidationRejectsInvalid:
    """validate_schema rejects malformed examples with specific field errors."""

    async def test_rejects_too_few_messages(self, tmp_path):
        """Rejects when messages has fewer than 3 items.

        Pydantic's min_length=3 constraint on TrainingExample.messages
        raises ValidationError at construction time, preventing invalid
        examples from being created in the first place.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="too_short"):
            TrainingExample(
                messages=[
                    ChatMessage(role="system", content="System prompt"),
                    ChatMessage(role="user", content="User query"),
                ],
                label=GreenwashVerdict.MISLEADING,
                severity=SeverityLevel.HIGH,
                sector="Energy",
                company="TestCorp",
            )

    async def test_rejects_missing_system_role(self, tmp_path):
        """Rejects when no message has role 'system'."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        msgs = [
            ChatMessage(role="user", content="First user message"),
            ChatMessage(role="user", content="Second user message"),
            ChatMessage(role="assistant", content="Assistant response"),
        ]
        example = _make_valid_example(messages=msgs)
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("system" in e for e in result.errors)

    async def test_rejects_missing_user_role(self, tmp_path):
        """Rejects when no message has role 'user'."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        msgs = [
            ChatMessage(role="system", content="System prompt"),
            ChatMessage(role="assistant", content="First response"),
            ChatMessage(role="assistant", content="Second response"),
        ]
        example = _make_valid_example(messages=msgs)
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("user" in e for e in result.errors)

    async def test_rejects_missing_assistant_role(self, tmp_path):
        """Rejects when no message has role 'assistant'."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        msgs = [
            ChatMessage(role="system", content="System prompt"),
            ChatMessage(role="user", content="User query"),
            ChatMessage(role="user", content="Another user message"),
        ]
        example = _make_valid_example(messages=msgs)
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("assistant" in e for e in result.errors)

    async def test_rejects_empty_sector(self, tmp_path):
        """Rejects when sector is empty string."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        example = _make_valid_example(sector="")
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("sector" in e for e in result.errors)

    async def test_rejects_whitespace_only_sector(self, tmp_path):
        """Rejects when sector is whitespace-only."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        example = _make_valid_example(sector="   ")
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("sector" in e for e in result.errors)

    async def test_rejects_empty_company(self, tmp_path):
        """Rejects when company is empty string."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        example = _make_valid_example(company="")
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("company" in e for e in result.errors)

    async def test_rejects_whitespace_only_company(self, tmp_path):
        """Rejects when company is whitespace-only."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        example = _make_valid_example(company="   ")
        result = await svc.validate_schema(example)
        assert result.valid is False
        assert any("company" in e for e in result.errors)

    async def test_multiple_errors_reported(self, tmp_path):
        """Reports multiple field errors when several fields are invalid."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        # Use 3 messages but missing the assistant role, plus empty sector and company
        msgs = [
            ChatMessage(role="system", content="System prompt"),
            ChatMessage(role="user", content="Only user"),
            ChatMessage(role="user", content="Another user"),
        ]
        example = _make_valid_example(messages=msgs, sector="", company="")
        result = await svc.validate_schema(example)
        assert result.valid is False
        # Should report errors for: missing assistant role, empty sector, empty company
        assert len(result.errors) >= 3


# ---------------------------------------------------------------------------
# Property 2: Storage round-trip
# ---------------------------------------------------------------------------


class TestStorageRoundTrip:
    """add_example → get_examples preserves all key fields."""

    async def test_round_trip_preserves_messages(self, tmp_path):
        """Stored and retrieved example has identical messages."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        original = _make_valid_example()
        stored = await svc.add_example(original)

        retrieved_list = await svc.get_examples()
        assert len(retrieved_list) == 1
        retrieved = retrieved_list[0]

        assert len(retrieved.messages) == len(stored.messages)
        for orig_msg, ret_msg in zip(stored.messages, retrieved.messages):
            assert orig_msg.role == ret_msg.role
            assert orig_msg.content == ret_msg.content

    async def test_round_trip_preserves_label(self, tmp_path):
        """Stored and retrieved example has same label."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for verdict in GreenwashVerdict:
            original = _make_valid_example(label=verdict)
            await svc.add_example(original)

        retrieved_list = await svc.get_examples(limit=100)
        labels = {ex.label for ex in retrieved_list}
        for verdict in GreenwashVerdict:
            assert verdict in labels

    async def test_round_trip_preserves_severity(self, tmp_path):
        """Stored and retrieved example has same severity."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        original = _make_valid_example(severity=SeverityLevel.MEDIUM)
        await svc.add_example(original)

        retrieved = (await svc.get_examples())[0]
        assert retrieved.severity == SeverityLevel.MEDIUM

    async def test_round_trip_preserves_sector_and_company(self, tmp_path):
        """Stored and retrieved example has same sector and company."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        original = _make_valid_example(sector="Fashion", company="GreenWear Inc")
        await svc.add_example(original)

        retrieved = (await svc.get_examples())[0]
        assert retrieved.sector == "Fashion"
        assert retrieved.company == "GreenWear Inc"

    async def test_round_trip_assigns_id(self, tmp_path):
        """Stored example gets a non-empty UUID id."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        original = _make_valid_example()
        stored = await svc.add_example(original)

        assert stored.id != ""
        retrieved = (await svc.get_examples())[0]
        assert retrieved.id == stored.id

    async def test_round_trip_preserves_source(self, tmp_path):
        """Stored and retrieved example has same source tag."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        original = _make_valid_example(source=ExampleSource.FEEDBACK)
        await svc.add_example(original)

        retrieved = (await svc.get_examples())[0]
        assert retrieved.source == ExampleSource.FEEDBACK


# ---------------------------------------------------------------------------
# Property 3: Dataset readiness thresholds
# ---------------------------------------------------------------------------


class TestDatasetReadinessThresholds:
    """is_evaluation_ready() and is_finetune_ready() follow threshold rules."""

    async def test_not_evaluation_ready_below_30(self, tmp_path):
        """is_evaluation_ready() returns False when N < 30."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for i in range(29):
            await svc.add_example(_make_valid_example(company=f"Corp{i}"))

        assert await svc.is_evaluation_ready() is False

    async def test_evaluation_ready_at_30(self, tmp_path):
        """is_evaluation_ready() returns True when N == 30."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for i in range(30):
            await svc.add_example(_make_valid_example(company=f"Corp{i}"))

        assert await svc.is_evaluation_ready() is True

    async def test_evaluation_ready_above_30(self, tmp_path):
        """is_evaluation_ready() returns True when N > 30."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for i in range(35):
            await svc.add_example(_make_valid_example(company=f"Corp{i}"))

        assert await svc.is_evaluation_ready() is True

    async def test_not_finetune_ready_below_200(self, tmp_path):
        """is_finetune_ready() returns False when N < 200."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        # Add 50 examples (well below 200)
        for i in range(50):
            await svc.add_example(_make_valid_example(company=f"Corp{i}"))

        assert await svc.is_finetune_ready() is False

    async def test_finetune_ready_at_200(self, tmp_path):
        """is_finetune_ready() returns True when N == 200."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for i in range(200):
            await svc.add_example(_make_valid_example(company=f"Corp{i}"))

        assert await svc.is_finetune_ready() is True

    async def test_empty_dataset_not_ready(self, tmp_path):
        """Both readiness checks return False for empty dataset."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        assert await svc.is_evaluation_ready() is False
        assert await svc.is_finetune_ready() is False

    async def test_dataset_stats_reflects_readiness(self, tmp_path):
        """get_dataset_stats() reports correct evaluation_ready and finetune_ready."""
        svc = TrainingPipelineService(data_dir=str(tmp_path))
        for i in range(30):
            await svc.add_example(_make_valid_example(company=f"Corp{i}"))

        stats = await svc.get_dataset_stats()
        assert stats.total_examples == 30
        assert stats.evaluation_ready is True
        assert stats.finetune_ready is False
