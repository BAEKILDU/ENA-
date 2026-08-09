"""Excel 읽기 공통 — engine 미지정 오류 방지."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def resolve_excel_engine(path: str | Path) -> str:
    """확장자/매직바이트로 pandas Excel engine 결정."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".xls":
        return "xlrd"
    if suffix in {".xlsx", ".xlsm"}:
        return "openpyxl"

    try:
        with p.open("rb") as f:
            head = f.read(8)
    except OSError:
        return "openpyxl"

    if head.startswith(b"PK"):
        return "openpyxl"
    if head.startswith(_OLE_MAGIC):
        return "xlrd"
    return "openpyxl"


def excel_file(path: str | Path, **kwargs: Any) -> pd.ExcelFile:
    if "engine" not in kwargs:
        kwargs["engine"] = resolve_excel_engine(path)
    return pd.ExcelFile(path, **kwargs)


def read_excel(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    if "engine" not in kwargs:
        kwargs["engine"] = resolve_excel_engine(path)
    return pd.read_excel(path, **kwargs)
