# Tasks

## Task 1: Implement Data Models and Training Pipeline Service
- [x] 1.1 Create `backend/models/training.py` with all Pydantic data models from design (TrainingExample, ChatMessage, GreenwashVerdict, SeverityLevel, ExampleSource, ValidationResult, DatasetStats)
- [x] 1.2 Create `backend/services/training_pipeline.py` implementing TrainingPipelineService with add_example(), validate_schema(), get_dataset_stats(), get_examples(), is_evaluation_ready(), is_finetune_ready()
- [x] 1.3 Store training data as JSONL files in `backend/data/training/` directory
- [x] 1.4 Add unit tests in `backend/tests/test_training_pipeline.py` verifying schema validation rejects invalid examples and accepts valid ones (Properties 1, 2, 3)

## Task 2: Implement Knowledge Base Service
- [-] 2.1 Create `backend/models/knowledge_base.py` with RegulatoryDocument, EnforcementAction, RetrievedPrecedent, KnowledgeBaseStats models
- [~] 2.2 Create `backend/services/knowledge_base.py` implementing KnowledgeBaseService with add_regulatory_document(), add_enforcement_action(), query_precedents(), get_stats()
- [~] 2.3 Use ChromaDB collection "knowledge_base" separate from document uploads, with metadata for jurisdiction and document type
- [~] 2.4 Add unit tests in `backend/tests/test_knowledge_base.py` verifying storage and retrieval of regulatory documents and enforcement actions

## Task 3: Implement Evaluation Framework
- [~] 3.1 Create `backend/models/evaluation.py` with MetricsResult, EvaluationReport, RegressionResult, Misclassification, PromptComparisonReport models
- [~] 3.2 Create `backend/services/evaluation_framework.py` implementing EvaluationFramework with run_evaluation(), compare_prompts(), check_regression(), compute_metrics()
- [~] 3.3 Implement precision/recall/F1 calculation per severity level with parallel execution for performance
- [~] 3.4 Add unit tests in `backend/tests/test_evaluation.py` verifying metrics computation and regression detection (Properties 5, 6, 7)

## Task 4: Implement Prompt Optimizer Service
- [~] 4.1 Create `backend/models/prompts.py` with PromptVersion, PromptExperiment, PromptEvaluationResult models
- [~] 4.2 Create `backend/services/prompt_optimizer.py` implementing PromptOptimizer with register_version(), evaluate_candidate(), promote(), rollback(), log_experiment()
- [~] 4.3 Store prompt versions as versioned files in `backend/data/prompts/` with metadata JSON sidecar
- [~] 4.4 Add unit tests in `backend/tests/test_prompt_optimizer.py` verifying version storage, promotion logic, and rollback (Properties 8, 9, 10, 11)

## Task 5: Implement Fine-Tuning Service
- [~] 5.1 Create `backend/models/finetuning.py` with DatasetSplits, BalanceResult, FineTuneConfig, FineTuneDataset models
- [~] 5.2 Create `backend/services/fine_tuning.py` implementing FineTuningService with export_dataset(), validate_balance(), generate_config(), split_dataset()
- [~] 5.3 Implement stratified splitting ensuring all severity levels appear in all splits
- [~] 5.4 Add unit tests in `backend/tests/test_fine_tuning.py` verifying JSONL export, stratified splits, and balance validation (Properties 12, 13, 14, 15)

## Task 6: Implement Hybrid Retrieval Service
- [~] 6.1 Create `backend/models/retrieval.py` with ScoredChunk, RankedChunk models
- [~] 6.2 Create `backend/services/hybrid_retrieval.py` implementing HybridRetrievalService with retrieve(), bm25_search(), rerank(), select_diverse()
- [~] 6.3 Add `rank_bm25` to requirements.txt and implement BM25 keyword search alongside existing vector search
- [~] 6.4 Implement cosine distance filtering (exclude chunks > 0.7 distance), named entity boosting, and diversity selection
- [~] 6.5 Add unit tests in `backend/tests/test_hybrid_retrieval.py` verifying hybrid retrieval, filtering, entity boosting, and diversity (Properties 4, 16, 17, 18, 19)

## Task 7: Implement Feedback Learning Service
- [~] 7.1 Create `backend/models/feedback.py` with UserCorrection, CorrectionResult, ConsensusResult, ConflictCheckResult models
- [~] 7.2 Create `backend/services/feedback_learning.py` implementing FeedbackLearningService with submit_correction(), check_consensus(), promote_to_dataset(), check_conflict(), get_pending_corrections()
- [~] 7.3 Store corrections as JSONL in `backend/data/feedback/` with provenance tagging (source="feedback" vs "expert")
- [~] 7.4 Add unit tests in `backend/tests/test_feedback_learning.py` verifying consensus threshold, conflict detection, and source tagging (Properties 20, 21, 22, 23)

## Task 8: Create API Routes
- [~] 8.1 Create `backend/routers/training.py` with POST /api/training/examples, GET /api/training/stats, GET /api/training/examples endpoints
- [~] 8.2 Create `backend/routers/evaluation.py` with POST /api/evaluation/run, POST /api/evaluation/compare, GET /api/evaluation/reports endpoints
- [~] 8.3 Create `backend/routers/prompts.py` with POST /api/prompts/versions, POST /api/prompts/evaluate, POST /api/prompts/promote, POST /api/prompts/rollback endpoints
- [~] 8.4 Create `backend/routers/feedback.py` with POST /api/feedback/corrections, GET /api/feedback/pending, POST /api/feedback/promote endpoints
- [~] 8.5 Register all new routers in `backend/main.py`

## Task 9: Integration and Seed Data
- [~] 9.1 Create `backend/data/training/seed_examples.jsonl` with 10 initial labeled greenwashing examples across energy, fashion, food sectors
- [~] 9.2 Create `backend/data/knowledge_base/ftc_green_guides.json` and `eu_green_claims.json` with regulatory document summaries
- [~] 9.3 Create `backend/data/knowledge_base/enforcement_actions.json` with 10 real enforcement action entries
- [~] 9.4 Add integration test in `backend/tests/test_integration_training.py` verifying end-to-end flow: add examples → evaluate → check readiness
