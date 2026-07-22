"""
닐슨 채널시청률 Excel → Supabase 업로드 (CLI)

사용법:
  1) sql/nielsen_channel_ratings.sql 실행
  2) python scripts/upload_nielsen_channel_ratings.py
  3) python scripts/upload_nielsen_channel_ratings.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from data.nielsen_ingest import parse_workbook, upload_nielsen_file  # noqa: E402


def find_default_file() -> Path | None:
    candidates = sorted(ROOT.glob("닐슨_채널시청률*.xls*"), reverse=True)
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description="닐슨 채널시청률 → Supabase 업로드")
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = args.file or find_default_file()
    if path is None or not path.exists():
        print("엑셀 파일을 찾을 수 없습니다. --file 로 경로를 지정하세요.", file=sys.stderr)
        return 1

    path = path.resolve()
    print(f"파일: {path}")
    if args.dry_run:
        report_date, tables = parse_workbook(path)
        print(f"분석일: {report_date}")
        for table, rows in tables.items():
            print(f"  parsed {table}: {len(rows)}")
        print("[--dry-run] DB 업로드 생략")
        return 0

    summary = upload_nielsen_file(path)
    print(f"분석일: {summary['report_date']}")
    print(summary)
    print("업로드 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
