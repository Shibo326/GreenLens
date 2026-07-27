"""PromptOptimizer -- manages prompt versioning, A/B testing, and promotion/rollback."""
import json
import logging
import os
import re
from datetime import datetime
from uuid import uuid4

from models.evaluation import MetricsResult
from models.prompts import PromptVersion, PromptExperiment, PromptEvaluationResult

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prompts")

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class PromptOptimizer:
    """Manages prompt versioning, A/B testing, and promotion/rollback logic."""

    def __init__(self, data_dir: str | None = None, evaluation_framework=None):
        self.data_dir = data_dir or _DATA_DIR
        self.evaluation_framework = evaluation_framework
        os.makedirs(self.data_dir, exist_ok=True)

    async def register_version(
        self, prompt_name: str, content: str, version: str
    ) -> PromptVersion:
        """Register a new prompt version with semantic versioning."""
        if not SEMVER_PATTERN.match(version):
            raise ValueError(
                f"Invalid semantic version format: '{version}'. Expected format: X.Y.Z"
            )

        prompt_dir = os.path.join(self.data_dir, prompt_name)
        os.makedirs(prompt_dir, exist_ok=True)

        # Write prompt content file
        content_path = os.path.join(prompt_dir, f"{version}.txt")
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Create metadata
        prompt_version = PromptVersion(
            name=prompt_name,
            version=version,
            content=content,
            is_production=False,
            created_at=datetime.utcnow(),
        )

        # Write metadata file
        meta_path = os.path.join(prompt_dir, f"{version}.meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(prompt_version.model_dump_json(indent=2))

        logger.info(f"Registered prompt '{prompt_name}' version {version}")
        return prompt_version

    async def evaluate_candidate(
        self, prompt_name: str, candidate_version: str
    ) -> PromptEvaluationResult:
        """Run evaluation on a candidate and compare to production."""
        production_version = await self._get_production_version(prompt_name)
        prod_version_str = production_version if production_version else "none"

        # Delegate to EvaluationFramework if available
        if self.evaluation_framework and production_version:
            candidate_content = await self._read_content(prompt_name, candidate_version)
            production_content = await self._read_content(prompt_name, production_version)
            comparison = await self.evaluation_framework.compare_prompts(
                candidate_content, production_content
            )
            candidate_metrics = comparison.prompt_a_metrics
            production_metrics = comparison.prompt_b_metrics
        else:
            # Return placeholder metrics when no evaluation framework or no production version
            candidate_metrics = MetricsResult(
                per_category={}, overall_accuracy=0.0, overall_f1=0.0, avg_response_time_ms=0.0
            )
            production_metrics = MetricsResult(
                per_category={}, overall_accuracy=0.0, overall_f1=0.0, avg_response_time_ms=0.0
            )

        is_improvement = self._check_improvement(candidate_metrics, production_metrics)
        recommendation = (
            "Promote candidate" if is_improvement else "Keep current production version"
        )

        return PromptEvaluationResult(
            candidate_version=candidate_version,
            production_version=prod_version_str,
            candidate_metrics=candidate_metrics,
            production_metrics=production_metrics,
            is_improvement=is_improvement,
            recommendation=recommendation,
        )

    async def promote(self, prompt_name: str, version: str) -> bool:
        """Promote version to production if it beats current on all severity categories."""
        prompt_dir = os.path.join(self.data_dir, prompt_name)
        meta_path = os.path.join(prompt_dir, f"{version}.meta.json")

        if not os.path.exists(meta_path):
            logger.warning(f"Version {version} not found for prompt '{prompt_name}'")
            return False

        # Load candidate metadata
        candidate = await self._load_version_metadata(prompt_name, version)
        if candidate is None:
            return False

        # Check if there's an existing production version to compare against
        current_prod_version = await self._get_production_version(prompt_name)
        if current_prod_version:
            current_prod = await self._load_version_metadata(prompt_name, current_prod_version)
            if current_prod and current_prod.evaluation_scores and candidate.evaluation_scores:
                # Candidate must beat production on all severity categories
                if not self._check_improvement(
                    candidate.evaluation_scores, current_prod.evaluation_scores
                ):
                    logger.info(
                        f"Version {version} does not beat production {current_prod_version} "
                        f"on all categories"
                    )
                    return False

        # Update production.json
        production_data = await self._read_production_file(prompt_name)
        production_data["previous_version"] = production_data.get("active_version")
        production_data["active_version"] = version
        production_data["promoted_at"] = datetime.utcnow().isoformat()
        await self._write_production_file(prompt_name, production_data)

        # Update version metadata
        candidate.is_production = True
        meta_path = os.path.join(prompt_dir, f"{version}.meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(candidate.model_dump_json(indent=2))

        # Demote old production version if exists
        if current_prod_version and current_prod_version != version:
            old_meta_path = os.path.join(prompt_dir, f"{current_prod_version}.meta.json")
            if os.path.exists(old_meta_path):
                old_prod = await self._load_version_metadata(prompt_name, current_prod_version)
                if old_prod:
                    old_prod.is_production = False
                    with open(old_meta_path, "w", encoding="utf-8") as f:
                        f.write(old_prod.model_dump_json(indent=2))

        logger.info(f"Promoted prompt '{prompt_name}' to version {version}")
        return True

    async def rollback(self, prompt_name: str) -> str:
        """Roll back to the previous production version. Return the restored version string."""
        production_data = await self._read_production_file(prompt_name)
        previous_version = production_data.get("previous_version")

        if not previous_version:
            raise ValueError(
                f"No previous version available for rollback on prompt '{prompt_name}'"
            )

        current_version = production_data.get("active_version")

        # Swap: previous becomes active, current becomes previous
        production_data["active_version"] = previous_version
        production_data["previous_version"] = current_version
        production_data["rolled_back_at"] = datetime.utcnow().isoformat()
        await self._write_production_file(prompt_name, production_data)

        # Update metadata for restored version
        prompt_dir = os.path.join(self.data_dir, prompt_name)
        restored_meta_path = os.path.join(prompt_dir, f"{previous_version}.meta.json")
        if os.path.exists(restored_meta_path):
            restored = await self._load_version_metadata(prompt_name, previous_version)
            if restored:
                restored.is_production = True
                with open(restored_meta_path, "w", encoding="utf-8") as f:
                    f.write(restored.model_dump_json(indent=2))

        # Demote current version
        if current_version:
            demoted_meta_path = os.path.join(prompt_dir, f"{current_version}.meta.json")
            if os.path.exists(demoted_meta_path):
                demoted = await self._load_version_metadata(prompt_name, current_version)
                if demoted:
                    demoted.is_production = False
                    with open(demoted_meta_path, "w", encoding="utf-8") as f:
                        f.write(demoted.model_dump_json(indent=2))

        logger.info(
            f"Rolled back prompt '{prompt_name}' from {current_version} to {previous_version}"
        )
        return previous_version

    async def log_experiment(self, experiment: PromptExperiment) -> None:
        """Append experiment to a JSONL log file."""
        prompt_dir = os.path.join(self.data_dir, experiment.prompt_name)
        os.makedirs(prompt_dir, exist_ok=True)

        log_path = os.path.join(prompt_dir, "experiments.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(experiment.model_dump_json() + "\n")

        logger.debug(
            f"Logged experiment {experiment.id} for "
            f"'{experiment.prompt_name}' v{experiment.prompt_version}"
        )

    # ---- Private helpers ----

    def _check_improvement(
        self, candidate_metrics: MetricsResult, production_metrics: MetricsResult
    ) -> bool:
        """Check if candidate beats production on all severity categories' F1 scores."""
        # If production has no per-category data, candidate wins by default
        if not production_metrics.per_category:
            return True
        # If candidate has no per-category data, it cannot beat production
        if not candidate_metrics.per_category:
            return False

        for category in production_metrics.per_category:
            if category not in candidate_metrics.per_category:
                return False
            prod_f1 = production_metrics.per_category[category].get("f1", 0.0)
            cand_f1 = candidate_metrics.per_category[category].get("f1", 0.0)
            if cand_f1 <= prod_f1:
                return False
        return True

    async def _get_production_version(self, prompt_name: str) -> str | None:
        """Get the currently active production version for a prompt."""
        production_data = await self._read_production_file(prompt_name)
        return production_data.get("active_version")

    async def _read_production_file(self, prompt_name: str) -> dict:
        """Read the production.json for a prompt."""
        prompt_dir = os.path.join(self.data_dir, prompt_name)
        prod_path = os.path.join(prompt_dir, "production.json")
        if not os.path.exists(prod_path):
            return {}
        with open(prod_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def _write_production_file(self, prompt_name: str, data: dict) -> None:
        """Write the production.json for a prompt."""
        prompt_dir = os.path.join(self.data_dir, prompt_name)
        os.makedirs(prompt_dir, exist_ok=True)
        prod_path = os.path.join(prompt_dir, "production.json")
        with open(prod_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def _read_content(self, prompt_name: str, version: str) -> str:
        """Read the content of a specific prompt version."""
        content_path = os.path.join(self.data_dir, prompt_name, f"{version}.txt")
        if not os.path.exists(content_path):
            raise FileNotFoundError(
                f"Content file not found for prompt '{prompt_name}' version {version}"
            )
        with open(content_path, "r", encoding="utf-8") as f:
            return f.read()

    async def _load_version_metadata(
        self, prompt_name: str, version: str
    ) -> PromptVersion | None:
        """Load the metadata for a specific prompt version."""
        meta_path = os.path.join(self.data_dir, prompt_name, f"{version}.meta.json")
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PromptVersion.model_validate(data)
