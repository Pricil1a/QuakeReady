"""Validasi payload CSV sebelum penyimpanan permanen."""
from __future__ import annotations
import io
from typing import Callable
import pandas as pd

class DatasetError(ValueError):
    """CSV tidak dapat dibaca atau tidak sesuai dengan skema dataset."""

def validate_csv_payload(payload: bytes, cleaner: Callable[[pd.DataFrame], pd.DataFrame]) -> pd.DataFrame:
    """Parse dan bersihkan payload tanpa menyentuh file penyimpanan."""
    if not isinstance(payload, bytes) or not payload:
        raise DatasetError("CSV kosong. Tidak ada data yang disimpan.")
    try:
        raw = pd.read_csv(io.BytesIO(payload), low_memory=False)
        cleaned = cleaner(raw)
    except Exception as exc:
        raise DatasetError(f"Format CSV tidak cocok: {exc}") from exc
    if cleaned is None or cleaned.empty:
        raise DatasetError("CSV tidak memuat baris data valid setelah pemeriksaan.")
    return cleaned
