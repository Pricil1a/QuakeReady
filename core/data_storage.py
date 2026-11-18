"""Penyimpanan CSV lokal persisten dengan penggantian file secara atomik."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import tempfile
from typing import Callable
import pandas as pd
from core.data_validation import DatasetError, validate_csv_payload

ALLOWED_FILES = frozenset({
    "BMKG_Clean_Final.csv",
    "QuakeReady_Historis_1998_2024.csv",
    "QuakeReady_Klasifikasi_Tahunan_1998_2024.csv",
    "STGNN_Analysis_2025.csv",
})
REGISTRY_FILE = ".quakeready_registry.json"

def _ensure_allowed(filename: str) -> None:
    if filename not in ALLOWED_FILES:
        raise DatasetError("Nama file di luar empat dataset yang diizinkan.")

def _atomic_write(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".qr_", suffix=".tmp", delete=False)
    temporary_path = Path(handle.name)
    try:
        with handle as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)

def registry(data_dir: Path) -> dict:
    registry_path = Path(data_dir) / REGISTRY_FILE
    if not registry_path.exists():
        return {}
    try:
        stored = json.loads(registry_path.read_text(encoding="utf-8"))
        return stored if isinstance(stored, dict) else {}
    except (ValueError, OSError):
        return {}

def save_dataset(data_dir: Path, filename: str, payload: bytes,
                 cleaner: Callable[[pd.DataFrame], pd.DataFrame]) -> dict:
    _ensure_allowed(filename)
    cleaned = validate_csv_payload(payload, cleaner)
    digest = hashlib.sha256(payload).hexdigest()
    record = {
        "sha256": digest, "file_size_bytes": len(payload),
        "validated_rows": int(len(cleaned)),
        "saved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filename": filename,
    }
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    _atomic_write(base / filename, payload)
    metadata = registry(base)
    metadata[filename] = record
    _atomic_write(base / REGISTRY_FILE, json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))
    return record

def remove_dataset(data_dir: Path, filename: str) -> None:
    _ensure_allowed(filename)
    base = Path(data_dir)
    (base / filename).unlink(missing_ok=True)
    metadata = registry(base)
    metadata.pop(filename, None)
    _atomic_write(base / REGISTRY_FILE, json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))

def file_revision(data_dir: Path, filename: str) -> tuple[int, int] | None:
    _ensure_allowed(filename)
    path = Path(data_dir) / filename
    if not path.is_file():
        return None
    stat_result = path.stat()
    return stat_result.st_mtime_ns, stat_result.st_size
