"""Armazenamento simples de vagas em JSON."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
JOBS_FILE = DATA_DIR / "jobs.json"

_lock = threading.Lock()


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not JOBS_FILE.exists():
        JOBS_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict[str, Any]]:
    _ensure_storage()
    raw = JOBS_FILE.read_text(encoding="utf-8") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _write_all(jobs: list[dict[str, Any]]) -> None:
    _ensure_storage()
    JOBS_FILE.write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_jobs() -> list[dict[str, Any]]:
    with _lock:
        return _read_all()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        for job in _read_all():
            if job["id"] == job_id:
                return job
    return None


def create_job(titulo: str, descricao: str, requisitos: str = "") -> dict[str, Any]:
    job = {
        "id": str(uuid.uuid4()),
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "requisitos": requisitos.strip(),
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        jobs = _read_all()
        jobs.append(job)
        _write_all(jobs)
    return job


def update_job(
    job_id: str,
    titulo: str | None = None,
    descricao: str | None = None,
    requisitos: str | None = None,
) -> dict[str, Any] | None:
    with _lock:
        jobs = _read_all()
        for job in jobs:
            if job["id"] == job_id:
                if titulo is not None:
                    job["titulo"] = titulo.strip()
                if descricao is not None:
                    job["descricao"] = descricao.strip()
                if requisitos is not None:
                    job["requisitos"] = requisitos.strip()
                _write_all(jobs)
                return job
    return None


def delete_job(job_id: str) -> bool:
    with _lock:
        jobs = _read_all()
        new_jobs = [job for job in jobs if job["id"] != job_id]
        if len(new_jobs) == len(jobs):
            return False
        _write_all(new_jobs)
        return True
