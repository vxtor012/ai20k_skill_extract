from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from .types import ArtifactManifest


def compute_sha256(content: str | bytes | Path) -> str:
    """Compute deterministic SHA-256 hash for raw string, bytes, or file content."""
    hasher = hashlib.sha256()
    if isinstance(content, Path):
        hasher.update(content.read_bytes())
    elif isinstance(content, str):
        hasher.update(content.encode("utf-8"))
    else:
        hasher.update(content)
    return hasher.hexdigest()[:12]


def build_manifest(
    version: str,
    prompt_path: Path,
    tools_path: Path,
    extra_files: list[Path] | None = None,
) -> ArtifactManifest:
    """Build immutable artifact manifest with content hashes."""
    prompt_hash = compute_sha256(prompt_path) if prompt_path.exists() else "missing"
    tools_hash = compute_sha256(tools_path) if tools_path.exists() else "missing"
    extra_hashes = {}
    if extra_files:
        for p in extra_files:
            if p.exists():
                extra_hashes[p.name] = compute_sha256(p)
    return ArtifactManifest(
        version=version,
        prompt_hash=prompt_hash,
        tools_hash=tools_hash,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        extra_hashes=extra_hashes,
    )


def log_experiment_iteration(
    log_file: Path,
    *,
    version: str,
    hypothesis: str,
    metrics: dict[str, float | int],
    run_file: str,
    notes: str = "",
) -> None:
    """Append structured experiment record to version_log.csv."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp",
        "version",
        "hypothesis",
        "total_cases",
        "pass_rate",
        "routing_acc",
        "args_acc",
        "extra_calls_rate",
        "run_file",
        "notes",
    ]
    file_exists = log_file.exists() and log_file.stat().st_size > 0
    with log_file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "version": version,
            "hypothesis": hypothesis,
            "total_cases": metrics.get("total_cases", 0),
            "pass_rate": f"{metrics.get('pass_rate', 0.0):.2%}",
            "routing_acc": f"{metrics.get('routing_accuracy', 0.0):.2%}",
            "args_acc": f"{metrics.get('args_accuracy', 0.0):.2%}",
            "extra_calls_rate": f"{metrics.get('extra_calls_rate', 0.0):.2%}",
            "run_file": run_file,
            "notes": notes,
        })
