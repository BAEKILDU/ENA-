"""
오리지널 콘텐츠 관리 Excel → CSV + Supabase 적용 CLI

  python scripts/extract_and_apply_original_content.py
  python scripts/extract_and_apply_original_content.py --dry-run
  python scripts/extract_and_apply_original_content.py --file "경로.xlsx"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from data.original_content_ingest import apply_original_workbook  # noqa: E402


def find_default_file() -> Path | None:
    for pattern in ("*0802*.xlsx", "*오리지널*콘텐츠*관리*.xlsx"):
        cands = sorted(
            (p for p in ROOT.glob(pattern) if not p.name.startswith("~$")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if cands:
            return cands[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="오리지널 콘텐츠 엑셀 → CSV + 업로드 적용")
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    args = parser.parse_args()

    path = args.file or find_default_file()
    if path is None or not path.exists():
        print("엑셀 파일을 찾을 수 없습니다. --file 로 지정하세요.", file=sys.stderr)
        return 1

    summary = apply_original_workbook(
        path,
        dry_run=args.dry_run or args.skip_upload,
        original_name=path.name,
    )
    print(f"파일: {summary['source_file']}")
    print(f"기준일: {summary['report_date']}")
    print(f"건수: {summary['counts']}")
    print(f"CSV: {summary['csv_files']}")
    print(f"업로드: {summary['uploaded']}")
    if summary.get("dry_run"):
        print("[dry-run/skip-upload] DB 업로드 생략 또는 시뮬레이션")
    print("완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
