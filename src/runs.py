"""Instrumentacao do pipeline: run_id, duracao, linhas, resultado por regra e versao de codigo/seed.

O pipeline grava data/analytics/run_report.json (artefato local, ignorado pelo git). `python -m src.db load`
le esse relatorio e persiste em ops.pipeline_runs e ops.data_quality_results.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
RUN_REPORT = ROOT / "data" / "analytics" / "run_report.json"
RUN_COLUMNS = ("run_id", "started_at", "finished_at", "duration_ms", "status", "code_version", "seed", "contract_version", "rows_by_entity", "error")


def code_version() -> str:
    """Hash curto do commit (com sufixo -dirty se ha alteracoes locais); CODE_VERSION no ambiente tem prioridade."""
    if os.environ.get("CODE_VERSION"):
        return os.environ["CODE_VERSION"]
    try:
        def git(*args: str) -> str:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=True).stdout.strip()

        return git("rev-parse", "--short", "HEAD") + ("-dirty" if git("status", "--porcelain") else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


class PipelineRun:
    def __init__(self, seed: int, contract_version: str):
        self.run_id = str(uuid.uuid4())
        self.seed = seed
        self.contract_version = contract_version
        self.started_at = datetime.now(timezone.utc)
        self._t0 = time.perf_counter()
        self.rows_by_entity: dict[str, int] = {}
        self.rules: list[dict] = []
        self.models: list[dict] = []
        self.drift: list[dict] = []

    def finish(self, status: str, error: str | None = None) -> dict:
        finished = datetime.now(timezone.utc)
        return {
            "run_id": self.run_id, "started_at": self.started_at.isoformat(), "finished_at": finished.isoformat(),
            "duration_ms": int((time.perf_counter() - self._t0) * 1000), "status": status,
            "code_version": code_version(), "seed": self.seed, "contract_version": self.contract_version,
            "rows_by_entity": self.rows_by_entity, "error": error, "rules": self.rules,
                        "models": self.models, "drift": self.drift,
                    }


def write_run_report(report: dict, path: Path = RUN_REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def read_run_report(path: Path = RUN_REPORT) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
