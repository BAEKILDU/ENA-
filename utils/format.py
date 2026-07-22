"""숫자·금액 포맷 유틸."""


def format_revenue_won(revenue_million: float | int) -> str:
    """백만 원 단위 데이터를 억 원 단위 문자열로 변환."""
    eok = float(revenue_million) / 100.0
    if abs(eok) >= 10:
        return f"{eok:.1f}억원"
    return f"{eok:.2f}억원"
