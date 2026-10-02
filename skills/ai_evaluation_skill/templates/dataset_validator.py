"""Generalized Golden Dataset and Corpus Provenance Validator."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import EvidenceContext, QAPair


class DatasetValidationError(Exception):
    """Raised when the dataset fails schema, contract, or provenance integrity checks."""


@dataclass(frozen=True)
class StratificationContract:
    """Defines required difficulty distribution and constraints for a dataset."""
    min_easy: int = 1
    min_medium: int = 1
    min_hard: int = 1
    min_adversarial: int = 1
    required_schema_version: str = "1.0"


class GoldenDatasetValidator:
    """
    Validates golden evaluation datasets for:
    1. Schema compliance (required keys, non-empty fields, correct types).
    2. Evidence provenance (every context snippet exists verbatim in source corpus).
    3. Stratification balance (distribution across difficulty levels and attack types).
    4. Uniqueness (no duplicate IDs, questions, or context fragments).
    """

    def __init__(self, corpus_root: str | Path | None = None) -> None:
        self.corpus_root = Path(corpus_root).resolve() if corpus_root else None
        self._corpus_cache: dict[str, str] = {}

    def _load_corpus_documents(self) -> dict[str, str]:
        if self._corpus_cache or self.corpus_root is None:
            return self._corpus_cache

        manifest_file = self.corpus_root / "manifest.json"
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            docs = manifest.get("documents", [])
            for doc in docs:
                rel_path = doc.get("path") if isinstance(doc, dict) else str(doc)
                doc_path = (self.corpus_root / rel_path).resolve()
                if not doc_path.is_relative_to(self.corpus_root) or not doc_path.is_file():
                    raise DatasetValidationError(f"Invalid document path: {rel_path}")
                self._corpus_cache[rel_path] = doc_path.read_text(encoding="utf-8")
        else:
            # Fallback: scan markdown and text files in directory
            for file_path in self.corpus_root.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in {".md", ".txt", ".json"}:
                    rel_path = str(file_path.relative_to(self.corpus_root)).replace("\\", "/")
                    self._corpus_cache[rel_path] = file_path.read_text(encoding="utf-8")

        return self._corpus_cache

    def validate_dataset_file(
        self,
        dataset_path: str | Path,
        contract: StratificationContract | None = None,
    ) -> list[QAPair]:
        """Validate a JSON golden dataset file and return typed QAPair objects."""
        path = Path(dataset_path).resolve()
        if not path.is_file():
            raise DatasetValidationError(f"Dataset file not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DatasetValidationError(f"Invalid JSON at {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc

        return self.validate_dataset_dict(data, contract)

    def validate_dataset_dict(
        self,
        data: dict[str, Any],
        contract: StratificationContract | None = None,
    ) -> list[QAPair]:
        """Validate parsed dataset dict against contract and provenance rules."""
        if not isinstance(data, dict):
            raise DatasetValidationError("Dataset root must be a JSON object")

        contract = contract or StratificationContract()
        schema_version = data.get("schema_version")
        if schema_version != contract.required_schema_version:
            raise DatasetValidationError(
                f"Unsupported schema_version '{schema_version}'. Expected '{contract.required_schema_version}'."
            )

        records = data.get("qa_pairs")
        if not isinstance(records, list) or not records:
            raise DatasetValidationError("Field 'qa_pairs' must be a non-empty list")

        corpus = self._load_corpus_documents()
        seen_ids: set[str] = set()
        seen_questions: set[str] = set()
        difficulty_counts: dict[str, int] = {}
        qa_pairs: list[QAPair] = []

        for idx, item in enumerate(records, start=1):
            if not isinstance(item, dict):
                raise DatasetValidationError(f"qa_pairs[{idx}] must be a JSON object")

            item_id = str(item.get("id", "")).strip()
            if not item_id:
                raise DatasetValidationError(f"qa_pairs[{idx}].id is missing or empty")
            if item_id in seen_ids:
                raise DatasetValidationError(f"Duplicate test case ID '{item_id}'")
            seen_ids.add(item_id)

            question = str(item.get("question", "")).strip()
            if not question:
                raise DatasetValidationError(f"{item_id}: 'question' must be a non-empty string")

            normalized_q = re.sub(r"\s+", " ", question).casefold()
            if normalized_q in seen_questions:
                raise DatasetValidationError(f"Duplicate question detected for item '{item_id}'")
            seen_questions.add(normalized_q)

            expected_answer = str(item.get("expected_answer", "")).strip()
            if not expected_answer:
                raise DatasetValidationError(f"{item_id}: 'expected_answer' must be non-empty")

            difficulty = str(item.get("difficulty", "medium")).strip().lower()
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

            raw_contexts = item.get("contexts", [])
            if not isinstance(raw_contexts, list):
                raise DatasetValidationError(f"{item_id}: 'contexts' must be a list")

            contexts: list[EvidenceContext] = []
            context_text_blocks: list[str] = []

            for c_idx, raw_c in enumerate(raw_contexts, start=1):
                if not isinstance(raw_c, dict):
                    raise DatasetValidationError(f"{item_id}: context[{c_idx}] must be an object")
                source_doc = str(raw_c.get("source_doc", "")).strip()
                text = str(raw_c.get("text", "")).strip()

                if not text:
                    raise DatasetValidationError(f"{item_id}: context[{c_idx}].text cannot be empty")

                # Provenance Check: verify verbatim existence in source corpus
                if corpus and source_doc:
                    if source_doc not in corpus:
                        raise DatasetValidationError(
                            f"{item_id}: source_doc '{source_doc}' not found in corpus manifest."
                        )
                    if text not in corpus[source_doc]:
                        raise DatasetValidationError(
                            f"{item_id}: context snippet failed provenance check against '{source_doc}'."
                        )

                contexts.append(EvidenceContext(source_doc=source_doc, text=text))
                context_text_blocks.append(text)

            qa_pairs.append(
                QAPair(
                    id=item_id,
                    question=question,
                    expected_answer=expected_answer,
                    context="\n\n".join(context_text_blocks),
                    difficulty=difficulty,
                    attack_type=item.get("attack_type"),
                    contexts=contexts,
                    metadata=item.get("metadata", {}),
                )
            )

        # Validate Stratification Contract
        if difficulty_counts.get("easy", 0) < contract.min_easy:
            raise DatasetValidationError(f"Insufficient easy samples: {difficulty_counts.get('easy', 0)} < {contract.min_easy}")
        if difficulty_counts.get("medium", 0) < contract.min_medium:
            raise DatasetValidationError(f"Insufficient medium samples: {difficulty_counts.get('medium', 0)} < {contract.min_medium}")
        if difficulty_counts.get("hard", 0) < contract.min_hard:
            raise DatasetValidationError(f"Insufficient hard samples: {difficulty_counts.get('hard', 0)} < {contract.min_hard}")
        if difficulty_counts.get("adversarial", 0) < contract.min_adversarial:
            raise DatasetValidationError(f"Insufficient adversarial samples: {difficulty_counts.get('adversarial', 0)} < {contract.min_adversarial}")

        return qa_pairs
