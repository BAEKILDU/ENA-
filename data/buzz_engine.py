"""콘텐츠 화제성 점수 종합 산정 엔진.

구성 지표
- 네이버 콘텐츠 화제성지수 (30%)
- 굿데이터(Fundex) 화제성 지수 (30%)
- 기사량 (20%)
- 커뮤니티 반응 (20%)

각 지표를 0~100으로 정규화한 뒤 가중 합산합니다.
"""

from __future__ import annotations

import math
from typing import Any

# 가중치 (합=1.0)
BUZZ_WEIGHTS: dict[str, float] = {
    "naver": 0.30,
    "gooddata": 0.30,
    "articles": 0.20,
    "community": 0.20,
}

COMPONENT_LABELS: dict[str, str] = {
    "naver": "네이버 콘텐츠 화제성지수",
    "gooddata": "굿데이터 화제성 지수",
    "articles": "기사량",
    "community": "커뮤니티 반응",
}


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def normalize_naver(raw: float | None) -> float | None:
    """네이버 화제성지수 → 0~100. 입력이 이미 0~100 또는 0~1000대면 보정."""
    if raw is None:
        return None
    v = float(raw)
    if v < 0:
        return 0.0
    if v <= 100:
        return round(v, 2)
    # 1000점 만점 스케일 가정
    if v <= 1000:
        return round(_clamp(v / 10.0), 2)
    return 100.0


def normalize_gooddata(raw: float | None) -> float | None:
    """굿데이터/Fundex 화제성(점유율% 또는 0~100 지수) → 0~100."""
    if raw is None:
        return None
    v = float(raw)
    if v < 0:
        return 0.0
    if v <= 1.0:
        # 0~1 비율
        return round(_clamp(v * 100.0), 2)
    if v <= 100:
        return round(v, 2)
    return round(_clamp(v), 2)


def normalize_articles(count: float | None, *, ref_max: float = 200.0) -> float | None:
    """기사량 → 0~100 (로그 스케일, ref_max편 ≈ 100점)."""
    if count is None:
        return None
    c = max(0.0, float(count))
    if c <= 0:
        return 0.0
    score = 100.0 * math.log1p(c) / math.log1p(ref_max)
    return round(_clamp(score), 2)


def normalize_community(raw: float | None) -> float | None:
    """커뮤니티 반응 점수(0~100) 또는 상대 지표."""
    if raw is None:
        return None
    v = float(raw)
    if v < 0:
        return 0.0
    if v <= 100:
        return round(v, 2)
    return round(_clamp(v), 2)


def _fallback_from_rating(rating: float | None) -> float:
    """지표 미입력 시 시청률 기반 추정 (표시용)."""
    r = float(rating or 0)
    return float(int(min(99, max(20, round(r * 80 + 35)))))


def compute_buzz_score(
    *,
    naver_index: float | None = None,
    gooddata_index: float | None = None,
    article_count: float | None = None,
    community_score: float | None = None,
    rating: float | None = None,
    article_ref_max: float = 200.0,
) -> dict[str, Any]:
    """종합 화제성 점수와 세부 산정 내역 반환.

    Returns
    -------
    dict with keys:
      buzz_index: int 0~100
      method: 'composite' | 'fallback_rating'
      components: list of breakdown rows
      formula: str
      weights: dict
    """
    norms = {
        "naver": normalize_naver(naver_index),
        "gooddata": normalize_gooddata(gooddata_index),
        "articles": normalize_articles(article_count, ref_max=article_ref_max),
        "community": normalize_community(community_score),
    }
    raws = {
        "naver": naver_index,
        "gooddata": gooddata_index,
        "articles": article_count,
        "community": community_score,
    }

    available = {k: v for k, v in norms.items() if v is not None}
    # 전부 0이면 미입력으로 간주 (관리자 폼 기본값 0 저장 방어)
    if available and all(float(v) == 0.0 for v in available.values()):
        available = {}
    components: list[dict[str, Any]] = []

    if not available:
        fb = _fallback_from_rating(rating)
        for key, w in BUZZ_WEIGHTS.items():
            components.append(
                {
                    "key": key,
                    "label": COMPONENT_LABELS[key],
                    "raw": None,
                    "normalized": None,
                    "weight": w,
                    "weight_effective": 0.0,
                    "contribution": 0.0,
                    "status": "미입력",
                }
            )
        return {
            "buzz_index": int(round(fb)),
            "method": "fallback_rating",
            "components": components,
            "formula": (
                f"입력 지표 없음 → 시청률 기반 추정 "
                f"min(99, max(20, round(시청률×80+35))) = {int(round(fb))}"
            ),
            "weights": dict(BUZZ_WEIGHTS),
            "note": "네이버·굿데이터·기사량·커뮤니티 지표를 관리자에서 입력하면 종합 산정으로 전환됩니다.",
        }

    # 가용 지표만으로 가중치 재정규화
    avail_weight_sum = sum(BUZZ_WEIGHTS[k] for k in available)
    total = 0.0
    for key, w in BUZZ_WEIGHTS.items():
        norm = norms[key]
        if norm is None:
            components.append(
                {
                    "key": key,
                    "label": COMPONENT_LABELS[key],
                    "raw": raws[key],
                    "normalized": None,
                    "weight": w,
                    "weight_effective": 0.0,
                    "contribution": 0.0,
                    "status": "미입력(재배분)",
                }
            )
            continue
        w_eff = w / avail_weight_sum if avail_weight_sum > 0 else 0.0
        contrib = norm * w_eff
        total += contrib
        components.append(
            {
                "key": key,
                "label": COMPONENT_LABELS[key],
                "raw": raws[key],
                "normalized": norm,
                "weight": w,
                "weight_effective": round(w_eff, 4),
                "contribution": round(contrib, 2),
                "status": "반영",
            }
        )

    score = int(round(_clamp(total)))
    parts = [
        f"{c['label']} {c['normalized']:.1f}×{c['weight_effective']*100:.0f}%"
        for c in components
        if c["normalized"] is not None
    ]
    formula = " + ".join(parts) + f" = {score}"

    return {
        "buzz_index": score,
        "method": "composite",
        "components": components,
        "formula": formula,
        "weights": dict(BUZZ_WEIGHTS),
        "note": "미입력 지표 가중치는 입력된 지표로 재배분됩니다.",
    }


def match_buzz_inputs(
    program_name: str,
    inputs_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """프로그램명 느슨 매칭."""
    if not program_name or not inputs_map:
        return None
    name = str(program_name).strip()
    if name in inputs_map:
        return inputs_map[name]
    norm = name.replace(" ", "").upper().replace("나는SOLO", "나는솔로")
    for k, v in inputs_map.items():
        kk = str(k).replace(" ", "").upper().replace("나는SOLO", "나는솔로")
        if norm == kk or norm in kk or kk in norm:
            return v
    return None
