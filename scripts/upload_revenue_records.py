"""
오리지널 콘텐츠 관리(매출/CAPEX) Excel → Supabase `revenue_records` 업로드 (CLI)

사용법:
  1) Supabase SQL Editor에서 sql/revenue_records.sql 실행
  2) python scripts/upload_revenue_records.py
  3) python scripts/upload_revenue_records.py --dry-run
  4) python scripts/upload_revenue_records.py --file "경로/파일.xlsx"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from data.revenue_ingest import parse_revenue_excel, upload_revenue_file  # noqa: E402


def find_default_file() -> Path | None:
    """루트에서 오리지널 콘텐츠 관리 xlsx를 우선 탐색."""
    patterns = (
        "*오리지널*콘텐츠*관리*.xlsx",
        "*오리지널*콘텐츠*관리*.xls",
        "*CAPEX*.xlsx",
        "*매출*.xlsx",
    )
    for pattern in patterns:
        candidates = sorted(ROOT.glob(pattern), reverse=True)
        # ~$ 임시 잠금 파일 제외
        candidates = [p for p in candidates if not p.name.startswith("~$")]
        if candidates:
            return candidates[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="오리지널 콘텐츠 관리(매출/CAPEX) → Supabase revenue_records 업로드"
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="업로드할 엑셀 경로 (미지정 시 프로젝트 루트에서 자동 탐색)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파싱만 수행하고 DB 업로드는 생략",
    )
    args = parser.parse_args()

    path = args.file or find_default_file()
    if path is None or not path.exists():
        print(
            "엑셀 파일을 찾을 수 없습니다. "
            '--file "◎ _26년 오리지널 콘텐츠 관리 (260101~0712 현재).xlsx" 로 지정하세요.',
            file=sys.stderr,
        )
        return 1

    path = path.resolve()
    print(f"파일: {path}")

    if args.dry_run:
        report_date, rows = parse_revenue_excel(path)
        print(f"기준일: {report_date}")
        print(f"  parsed revenue_records: {len(rows)}")
        for row in rows[:5]:
            print(
                f"  - {row['program_name']}: "
                f"{row['revenue_million']} (백만) · {row.get('category') or '-'}"
            )
        if len(rows) > 5:
            print(f"  … 외 {len(rows) - 5}건")
        print("[--dry-run] DB 업로드 생략")
        return 0

    summary = upload_revenue_file(path)
    print(f"기준일: {summary['report_date']}")
    print(f"소스: {summary['source_file']}")
    print(f"파싱: {summary['tables']}")
    print(f"업로드: {summary['uploaded']}")
    print("샘플:")
    for row in summary.get("sample") or []:
        print(f"  - {row['program_name']}: {row['revenue_million']}")
    print("업로드 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
