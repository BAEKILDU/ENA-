"""ENA 가치+ Mock 데이터 — 초기 UI 구성용 임시 데이터."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ── ENA 예능 콘텐츠 (방송 중) ──────────────────────────────────────────────
ENA_VARIETY_SHOWS = [
    {
        "id": "ena_001",
        "title": "ENA 먹을텐데",
        "genre": "푸드 예능",
        "slot": "수 22:00",
        "day": "수",
        "time": "22:00",
        "status": "방송중",
        "cast": ["이영자", "홍석천", "김희철"],
        "weeks_on_air": 8,
    },
    {
        "id": "ena_002",
        "title": "ENA 술래잡기",
        "genre": "서바이벌 예능",
        "slot": "금 23:00",
        "day": "금",
        "time": "23:00",
        "status": "방송중",
        "cast": ["유재석", "조세호", "이이경"],
        "weeks_on_air": 12,
    },
    {
        "id": "ena_003",
        "title": "ENA 글로벌 퀴즈쇼",
        "genre": "퀴즈 예능",
        "slot": "일 19:30",
        "day": "일",
        "time": "19:30",
        "status": "방송중",
        "cast": ["전현무", "장도연", "코드 Kunst"],
        "weeks_on_air": 5,
    },
    {
        "id": "ena_004",
        "title": "ENA 캠핑클럽",
        "genre": "리얼리티 예능",
        "slot": "토 21:00",
        "day": "토",
        "time": "21:00",
        "status": "방송중",
        "cast": ["은지원", "이수근", "김희철"],
        "weeks_on_air": 15,
    },
    {
        "id": "ena_005",
        "title": "ENA 웃음공장",
        "genre": "코미디 예능",
        "slot": "목 22:30",
        "day": "목",
        "time": "22:30",
        "status": "방송중",
        "cast": ["박나래", "장도연", "양세찬"],
        "weeks_on_air": 3,
    },
]

# 동시간대 경쟁 콘텐츠 (타 채널)
COMPETITOR_SHOWS = {
    "수 22:00": [
        {"channel": "ENA", "title": "ENA 먹을텐데", "is_ena": True},
        {"channel": "tvN", "title": "놀뭐", "is_ena": False},
        {"channel": "JTBC", "title": "한끼줍쇼", "is_ena": False},
        {"channel": "MBC", "title": "전지적 참견", "is_ena": False},
    ],
    "금 23:00": [
        {"channel": "ENA", "title": "ENA 술래잡기", "is_ena": True},
        {"channel": "SBS", "title": "런닝맨", "is_ena": False},
        {"channel": "tvN", "title": "놀뭐 스핀오프", "is_ena": False},
    ],
    "일 19:30": [
        {"channel": "ENA", "title": "ENA 글로벌 퀴즈쇼", "is_ena": True},
        {"channel": "KBS2", "title": "1박2일", "is_ena": False},
        {"channel": "MBC", "title": "나 혼자 산다", "is_ena": False},
    ],
    "토 21:00": [
        {"channel": "ENA", "title": "ENA 캠핑클럽", "is_ena": True},
        {"channel": "tvN", "title": "놀뭐", "is_ena": False},
        {"channel": "JTBC", "title": "놀면 뭐하니", "is_ena": False},
    ],
    "목 22:30": [
        {"channel": "ENA", "title": "ENA 웃음공장", "is_ena": True},
        {"channel": "SBS", "title": "동상이몽", "is_ena": False},
        {"channel": "tvN", "title": "유퀴즈", "is_ena": False},
    ],
}

# 시청률·화제성·매출 지표 (Mock)
PERFORMANCE_METRICS = {
    "ena_001": {
        "rating": 1.8,
        "buzz_index": 72,
        "revenue_million": 450,
        "trend": "상승",
        "rating_history": [1.2, 1.4, 1.5, 1.6, 1.7, 1.75, 1.8, 1.8],
        "target_rating": 1.5,
        "target_buzz": 65,
        "target_revenue_million": 400,
    },
    "ena_002": {
        "rating": 2.4,
        "buzz_index": 88,
        "revenue_million": 820,
        "trend": "유지",
        "rating_history": [2.1, 2.2, 2.3, 2.4, 2.5, 2.4, 2.4, 2.4],
        "target_rating": 2.5,
        "target_buzz": 85,
        "target_revenue_million": 800,
    },
    "ena_003": {
        "rating": 1.1,
        "buzz_index": 45,
        "revenue_million": 180,
        "trend": "하락",
        "rating_history": [1.5, 1.4, 1.3, 1.2, 1.1, 1.1, 1.0, 1.1],
        "target_rating": 1.6,
        "target_buzz": 55,
        "target_revenue_million": 250,
    },
    "ena_004": {
        "rating": 2.8,
        "buzz_index": 91,
        "revenue_million": 1100,
        "trend": "상승",
        "rating_history": [2.0, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8, 2.8],
        "target_rating": 2.5,
        "target_buzz": 80,
        "target_revenue_million": 950,
    },
    "ena_005": {
        "rating": 0.9,
        "buzz_index": 38,
        "revenue_million": 95,
        "trend": "하락",
        "rating_history": [1.2, 1.1, 1.0, 0.95, 0.9, 0.9, 0.85, 0.9],
        "target_rating": 1.4,
        "target_buzz": 50,
        "target_revenue_million": 200,
    },
}

# 종영 콘텐츠 (신규 기획 비교용)
ENDED_SHOWS = [
    {
        "title": "ENA 미식탐험대",
        "genre": "푸드 예능",
        "slot": "수 22:00",
        "cast": ["백종원", "성시경"],
        "avg_rating": 2.1,
        "buzz_index": 78,
        "revenue_million": 620,
        "ended": "2025-12",
    },
    {
        "title": "ENA 서바이벌 킹",
        "genre": "서바이벌 예능",
        "slot": "금 23:00",
        "cast": ["김종국", "하하"],
        "avg_rating": 1.9,
        "buzz_index": 65,
        "revenue_million": 380,
        "ended": "2025-09",
    },
    {
        "title": "ENA 리얼캠프",
        "genre": "리얼리티 예능",
        "slot": "토 21:00",
        "cast": ["이수근", "은지원"],
        "avg_rating": 2.5,
        "buzz_index": 82,
        "revenue_million": 750,
        "ended": "2025-11",
    },
]

REVENUE_IDEAS_TEMPLATES = [
    {
        "category": "굿즈",
        "ideas": [
            "출연진 시그니처 아이템 한정판 굿즈 (앞치마·머그컵 등)",
            "콘텐츠 로고·캐릭터 IP 라이선싱 — 편의점·카페 콜라보",
            "시즌별 포토북·비하인드 스토리북 한정 판매",
        ],
    },
    {
        "category": "팝업·체험",
        "ideas": [
            "콘텐츠 세트 재현 팝업스토어 (체험·포토존·굿즈 판매)",
            "출연진 레시피·게임 룰 기반 체험형 팝업 (MZ 타겟)",
            "전국 투어형 팝업 — 지역별 한정 굿즈·이벤트",
        ],
    },
    {
        "category": "디지털·OTT",
        "ideas": [
            "미공개 클립·비하인드 OTT/VOD 프리미엄 패키지",
            "콘텐츠 연계 숏폼·릴스 채널 광고·브랜디드 콘텐츠",
            "인터랙티브 퀴즈·게임 앱 (시청률 연계 이벤트)",
        ],
    },
    {
        "category": "브랜드·광고",
        "ideas": [
            "PPL 연계 브랜드 공동 마케팅 (식품·생활·여행)",
            "콘텐츠 테마 숙박·여행 패키지 (캠핑·미식 등)",
            "출연진 개별 브랜드 앰버서더 연계 크로스 프로모션",
        ],
    },
    {
        "category": "공연·이벤트",
        "ideas": [
            "시즌 종영 기념 팬미팅·토크쇼 (티켓·MD 수익)",
            "콘텐츠 게임·미션 재현 오프라인 이벤트",
            "출연진 콜라보 라이브 커머스 (한정 굿즈·식품)",
        ],
    },
]


def get_ena_variety_df() -> pd.DataFrame:
    """ENA 예능 콘텐츠 통합 DataFrame."""
    rows = []
    for show in ENA_VARIETY_SHOWS:
        metrics = PERFORMANCE_METRICS[show["id"]]
        rows.append({**show, **metrics})
    return pd.DataFrame(rows)


def get_top_bottom_groups() -> tuple[list[dict], list[dict]]:
    """시청률·화제성 기준 상위/하위 그룹."""
    df = get_ena_variety_df()
    df["value_score"] = df["rating"] * 30 + df["buzz_index"] * 0.7
    df = df.sort_values("value_score", ascending=False)
    top = df.head(2).to_dict("records")
    bottom = df.tail(2).to_dict("records")
    return top, bottom


def get_competition_data(slot: str) -> pd.DataFrame:
    """동시간대 경쟁 콘텐츠 시청률 Mock."""
    shows = COMPETITOR_SHOWS.get(slot, [])
    ratings = {
        "ENA 먹을텐데": 1.8,
        "놀뭐": 3.2,
        "한끼줍쇼": 1.5,
        "전지적 참견": 2.8,
        "ENA 술래잡기": 2.4,
        "런닝맨": 2.9,
        "놀뭐 스핀오프": 1.7,
        "ENA 글로벌 퀴즈쇼": 1.1,
        "1박2일": 4.5,
        "나 혼자 산다": 3.8,
        "ENA 캠핑클럽": 2.8,
        "놀면 뭐하니": 2.1,
        "ENA 웃음공장": 0.9,
        "동상이몽": 2.3,
        "유퀴즈": 3.5,
    }
    rows = []
    for s in shows:
        rows.append(
            {
                "channel": s["channel"],
                "title": s["title"],
                "is_ena": s["is_ena"],
                "rating": ratings.get(s["title"], round(random.uniform(0.8, 3.5), 1)),
            }
        )
    return pd.DataFrame(rows)


def get_trend_data(show_id: str, period: str = "week") -> pd.DataFrame:
    """주/월/연 단위 트렌드 Mock."""
    show = next(s for s in ENA_VARIETY_SHOWS if s["id"] == show_id)
    history = PERFORMANCE_METRICS[show_id]["rating_history"]

    if period == "week":
        labels = [f"{i + 1}주" for i in range(len(history))]
        values = history
    elif period == "month":
        labels = ["1월", "2월", "3월", "4월", "5월", "6월"]
        base = np.mean(history)
        values = [round(base + random.uniform(-0.3, 0.3), 2) for _ in labels]
    else:
        labels = ["2023", "2024", "2025", "2026"]
        base = np.mean(history)
        values = [round(base * f, 2) for f in [0.7, 0.85, 0.95, 1.0]]

    return pd.DataFrame({"period": labels, "rating": values, "title": show["title"]})


def get_weekly_summary() -> dict:
    """주간 핵심 요약."""
    df = get_ena_variety_df()
    top_show = df.loc[df["rating"].idxmax()]
    rising = df[df["trend"] == "상승"]
    return {
        "top_title": top_show["title"],
        "top_rating": top_show["rating"],
        "rising_count": len(rising),
        "avg_rating": round(df["rating"].mean(), 2),
        "total_revenue": df["revenue_million"].sum(),
    }


def get_goal_vs_actual_df() -> pd.DataFrame:
    """프로그램별 목표 대비 실적 DataFrame."""
    df = get_ena_variety_df().copy()
    df["rating_achv"] = (df["rating"] / df["target_rating"] * 100).round(1)
    df["buzz_achv"] = (df["buzz_index"] / df["target_buzz"] * 100).round(1)
    df["revenue_achv"] = (df["revenue_million"] / df["target_revenue_million"] * 100).round(1)
    df["overall_achv"] = ((df["rating_achv"] + df["buzz_achv"] + df["revenue_achv"]) / 3).round(1)
    df["goal_status"] = df["overall_achv"].apply(
        lambda x: "목표 달성" if x >= 100 else ("근접" if x >= 85 else "미달")
    )
    return df.sort_values("overall_achv", ascending=False)


def get_goal_summary() -> dict:
    """목표 대비 실적 요약 KPI."""
    df = get_goal_vs_actual_df()
    achieved = df[df["goal_status"] == "목표 달성"]
    return {
        "avg_achv": round(df["overall_achv"].mean(), 1),
        "achieved_count": len(achieved),
        "total_count": len(df),
        "avg_rating_achv": round(df["rating_achv"].mean(), 1),
        "avg_revenue_achv": round(df["revenue_achv"].mean(), 1),
        "top_title": df.iloc[0]["title"],
        "top_achv": df.iloc[0]["overall_achv"],
        "bottom_title": df.iloc[-1]["title"],
        "bottom_achv": df.iloc[-1]["overall_achv"],
    }


def parse_uploaded_proposal(filename: str, file_bytes: bytes | None = None) -> dict:
    """업로드 기획안 본문 추출·검증 후 메타데이터 반환."""
    from utils.proposal_parse import parse_proposal_document

    extracted = parse_proposal_document(filename, file_bytes or b"")
    data = extracted.to_dict()
    return {
        "title": data["title"],
        "genre": data["genre"],
        "slot": data["slot"],
        "channel": data["channel"],
        "cast": data["cast"],
        "logline": data["logline"],
        "intent": data["intent"],
        "source_file": data["source_file"] or filename,
        "extraction": data,
    }


def analyze_uploaded_proposal(filename: str, file_bytes: bytes | None = None) -> dict:
    """업로드 기획안 본문 분석 후 경쟁력 결과 생성."""
    parsed = parse_uploaded_proposal(filename, file_bytes)
    result = analyze_new_proposal(
        parsed["title"],
        parsed["genre"] if parsed["genre"] != "미정" else "리얼리티 예능",
        parsed["slot"] if parsed["slot"] != "미정" else "수 22:00",
        parsed["cast"],
    )
    result["source"] = "upload"
    result["source_file"] = parsed["source_file"]
    result["extraction"] = parsed.get("extraction", {})

    overview = result.get("overview") or {}
    overview["title"] = parsed["title"]
    overview["genre"] = parsed["genre"]
    overview["slot"] = parsed["slot"]
    overview["channel"] = parsed.get("channel") or overview.get("channel") or "ENA"
    overview["cast"] = [c.strip() for c in str(parsed["cast"]).split(",") if c.strip()] or ["미정"]
    if parsed.get("logline") and parsed["logline"] != "미정":
        overview["logline"] = parsed["logline"]
    result["overview"] = overview
    result["title"] = parsed["title"]
    result["genre"] = overview["genre"]
    result["slot"] = overview["slot"]
    result["cast"] = overview["cast"]

    # 추출된 기획의도·로그라인으로 요약 재구성
    if parsed.get("intent"):
        result.setdefault("summary", {})
        result["summary"]["intent"] = parsed["intent"]
        if result.get("swot") is not None:
            result["swot"]["intent_summary"] = parsed["intent"]

    return result


def _build_logline(title: str, genre: str, cast_list: list[str]) -> str:
    """장르·출연진 기반 Mock 로그라인."""
    cast_text = ", ".join(cast_list[:2]) if cast_list else "출연진"
    templates = {
        "푸드": f"{cast_text}가 전국 곳곳의 숨은 맛집을 찾아 떠나는 힐링 푸드 예능.",
        "서바이벌": f"일상 속 숨겨진 능력을 가진 사람들이 펼치는 서바이벌 리얼리티.",
        "퀴즈": f"{cast_text}와 함께하는 지식·상식 대결, 시청자 참여형 퀴즈 예능.",
        "리얼리티": f"{cast_text}가 낯선 공간에서 하루를 살아가며 보여주는 리얼리티 다큐 예능.",
        "코미디": f"{cast_text}의 유쾌한 케미로 매주 새로운 미션에 도전하는 코미디 예능.",
    }
    for key, line in templates.items():
        if key in genre:
            return line
    return f"{cast_text}가 함께하는 ENA 신규 예능 프로젝트."


def _build_intent_summary(title: str, genre: str, logline: str) -> str:
    """기획의도 및 내용 요약."""
    return (
        f"'{title}'은(는) {genre} 포맷으로, {logline} "
        f"시청 몰입과 화제성 확산을 목표로 한 ENA 신규 기획안입니다."
    )


def _build_swot_analysis(
    title: str,
    genre: str,
    slot: str,
    cast_list: list[str],
    scores: dict,
    overall: float,
    competition: list,
    logline: str,
) -> dict:
    """pro2 템플릿 — 강·약점 및 긍정·중립·부정 의견."""
    avg_comp = sum(c.get("rating", 0) for c in competition) / max(len(competition), 1)
    buzz = scores.get("화제성", 5)
    originality = scores.get("독창성", 5)
    mass = scores.get("대중성", 5)
    feasibility = scores.get("완성도/실현가능성", 5)
    scalability = scores.get("확장성", 5)
    cast_str = ", ".join(cast_list) if cast_list else "미정"

    strengths = [
        f"{genre} 포맷의 시청 유인 요소와 로그라인 기반 스토리 훅이 명확함",
        f"출연진({cast_str}) 케미·역할 분담을 통한 초반 관심 유도 가능",
    ]
    if originality >= 6.5:
        strengths.append("유사 콘텐츠 대비 차별화 포인트가 있어 포맷 신선도 확보에 유리")
    else:
        strengths.append(f"{slot} 편성 전략과 디지털 확산 연계로 초기 도달률을 보완할 수 있음")

    weaknesses = [
        f"{slot} 동시간대 경쟁 강도(평균 시청률 {avg_comp:.1f}%)로 진입 장벽이 존재",
        "타겟 시청층이 좁아질 경우 초반 시청률 변동 폭이 커질 수 있음",
    ]
    if feasibility < 7:
        weaknesses.append("제작 스케일·로케이션·연출 난이도에 따라 실현 리스크가 있음")
    else:
        weaknesses.append("유사 소재 증가 시 중장기 화제성 유지에 추가 기획이 필요")

    key_strength = strengths[0]
    key_risk = weaknesses[0]
    one_liner = (
        f"매력도는 양호하나 성공 가능성은 편성·출연진·차별화 보완에 좌우되는 "
        f"{overall}/10점 수준의 기획안"
        if overall < 7
        else f"차별화와 확장성이 뒷받침되면 성공 가능성이 높은 {overall}/10점 기획안"
    )

    positive = [
        f"종합 경쟁력 {overall}/10점으로 제작 검토 가치가 충분함",
        f"화제성 {buzz}/10 · 확장성 {scalability}/10 — 숏폼·IP 연계 수익 모델 설계에 유리",
        f"편성 시 {genre} 라인업 다양성 확보와 신규 시청층 유입에 기여 가능",
    ]
    neutral = [
        f"편성채널 ENA · {slot} — 시즌·회차 전략에 따라 성과 변동 가능",
        f"대중성 {mass}/10 기준으로 핵심 타깃과 확장 타깃의 균형 조정이 필요",
        "제작비·방영 시기·디지털 선배포 강도에 따라 ROI가 달라질 수 있음",
    ]
    negative = [
        f"동시간 경쟁 {max(len(competition), 1)}편 환경에서 상위권 안착이 쉽지 않을 수 있음",
        f"독창성 {originality}/10 — 유사 포맷 대비 열위가 드러나면 중반 이탈 리스크",
        "출연진 파워·포맷 피로도를 사전 보완하지 않으면 초반 화제성 소진 가능",
    ]

    if overall >= 7:
        final_conclusion = (
            f"'{title}'은(는) 강점 중심으로 편성·홍보를 설계하면 제작 추진을 권장할 수 있습니다. "
            f"핵심 강점({key_strength})을 전면에 배치하고, 치명적 리스크({key_risk})를 파일럿 단계에서 검증하세요."
        )
    elif overall >= 5:
        final_conclusion = (
            f"'{title}'은(는) 조건부 제작 검토가 적절합니다. "
            f"약점 보완과 포맷 검증을 선행한 뒤, 긍정 요인을 편성 전략에 반영하는 것을 제안합니다."
        )
    else:
        final_conclusion = (
            f"'{title}'은(는) 현 단계에서 기획 보완이 우선입니다. "
            f"출연·포맷·편성 전략을 재설계한 후 재평가를 권장합니다."
        )

    return {
        "intent_summary": _build_intent_summary(title, genre, logline),
        "one_liner": one_liner,
        "key_strength": key_strength,
        "key_risk": key_risk,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "final_conclusion": final_conclusion,
    }


def _build_score_details(cast_score: float, competition_score: float, format_score: float) -> dict:
    """pro2 5대 세부 지표 점수 + 이유."""
    buzz = round(min(10, (cast_score + format_score) / 2 + random.uniform(-0.3, 0.5)), 1)
    originality = round(min(10, format_score + random.uniform(-0.8, 0.8)), 1)
    mass = round(min(10, (cast_score + competition_score) / 2 + random.uniform(-0.4, 0.6)), 1)
    feasibility = round(min(10, 6.5 + random.uniform(-0.5, 1.5)), 1)
    scalability = round(min(10, (buzz + originality) / 2 + random.uniform(-0.3, 0.7)), 1)

    details = {
        "화제성": {
            "score": buzz,
            "reason": "출연진·포맷의 SNS/숏폼 확산 가능성과 초반 화제 훅 강도를 반영",
        },
        "독창성": {
            "score": originality,
            "reason": "유사 장르 대비 로그라인·룰셋 차별화 수준을 평가",
        },
        "대중성": {
            "score": mass,
            "reason": "핵심 타깃 외 일반 시청층 유입 가능성과 편성 접근성을 반영",
        },
        "완성도/실현가능성": {
            "score": feasibility,
            "reason": "제작 난이도, 로케이션·캐스팅 현실성, 회차 운영 가능성을 종합 평가",
        },
        "확장성": {
            "score": scalability,
            "reason": "IP·MD·디지털·글로벌 확장 등 부가사업 연계 가능성을 반영",
        },
    }
    scores = {k: v["score"] for k, v in details.items()}
    return scores, details


def analyze_new_proposal(
    title: str,
    genre: str,
    slot: str,
    cast: str,
) -> dict:
    """신규 기획안 Mock 분석 결과 (pro2 템플릿)."""
    cast_list = [c.strip() for c in cast.split(",") if c.strip()] or ["미정"]
    cast_score = min(10, max(3, len([c for c in cast_list if c != "미정"]) * 2 + random.randint(2, 4)))

    slot_competition = get_competition_data(slot)
    if slot_competition.empty or "rating" not in slot_competition.columns:
        avg_comp_rating = 2.0
        competition_records = []
    else:
        avg_comp_rating = float(slot_competition["rating"].mean())
        competition_records = slot_competition.to_dict("records")
    competition_score = max(1, min(10, round(10 - avg_comp_rating * 1.5, 1)))

    similar = [
        s
        for s in ENDED_SHOWS + [dict(s) for s in ENA_VARIETY_SHOWS]
        if genre.split()[0] in s.get("genre", "")
    ]
    format_score = 6.0
    if similar:
        avg_sim = np.mean([s.get("avg_rating", s.get("rating", 1.5)) for s in similar])
        format_score = min(10, round(avg_sim * 3, 1))

    scores, score_details = _build_score_details(cast_score, competition_score, format_score)
    overall = round(float(np.mean(list(scores.values()))), 1)
    logline = _build_logline(title, genre, cast_list)
    swot = _build_swot_analysis(
        title, genre, slot, cast_list, scores, overall, competition_records, logline
    )

    return {
        "title": title,
        "genre": genre,
        "slot": slot,
        "cast": cast_list,
        "scores": scores,
        "score_details": score_details,
        "overall": overall,
        "competition": competition_records,
        "similar_shows": similar[:3],
        "source": "manual",
        "overview": {
            "title": title or "미정",
            "genre": genre or "미정",
            "slot": slot or "미정",
            "channel": "ENA",
            "cast": cast_list,
            "logline": logline,
        },
        "swot": swot,
        "summary": {
            "intent": swot["intent_summary"],
            "one_liner": swot["one_liner"],
            "overall": overall,
            "key_strength": swot["key_strength"],
            "key_risk": swot["key_risk"],
        },
        "kpi": {
            "overall": overall,
            "required_cast": max(2, len([c for c in cast_list if c != "미정"])),
            "best_slot": slot or "미정",
            "competitor_count": max(len(competition_records), len(similar[:3]), 1),
        },
        "final_conclusion": swot["final_conclusion"],
    }


REVENUE_IDEAS_PRO2 = [
    {
        "category": "오프라인/공간 비즈니스",
        "ideas": [
            "몰입형 팝업 스토어 — 프로그램 세트·포토존·미션 체험 공간 운영",
            "테마 전시·방탈출 카페 연계 — 회차 미션을 오프라인 콘텐츠로 재구성",
            "지역 축제·관광지 콜라보 — 로케이션 기반 체험 패키지 판매",
        ],
    },
    {
        "category": "MD 및 굿즈 기획",
        "ideas": [
            "출연진/캐릭터 IP 활용 의류·액세서리·문구 라인 출시",
            "극 중 주요 소품 레플리카·한정판 키트 크라우드 판매",
            "시즌 포토북·비하인드 패키지 및 디지털 포토카드 판매",
        ],
    },
    {
        "category": "디지털/플랫폼 확장",
        "ideas": [
            "웹툰/웹소설 스핀오프 — 미공개 에피소드·평행 세계관 확장",
            "유튜브·숏폼 멤버십 — 미공개 클립·메이킹·라이브 토크",
            "인터랙티브 앱/메타버스 — 시청자 참여형 미션·아바타 월드",
        ],
    },
    {
        "category": "B2B 콜라보레이션",
        "ideas": [
            "F&B 브랜드 협업 메뉴·패키지 출시 및 PPL 연계 프로모션",
            "패션·라이프스타일 브랜드 한정판 협업 및 앰버서더 캠페인",
            "통신·OTT·커머스 플랫폼 공동 마케팅 패키지",
        ],
    },
    {
        "category": "글로벌 및 팬덤 비즈니스",
        "ideas": [
            "글로벌 라이선스 포맷 수출 및 현지화 리메이크",
            "팬미팅·콘서트·투어 이벤트와 MD 동시 판매",
            "크라우드 펀딩 기반 스페셜 에피소드·굿즈 프로젝트",
        ],
    },
]


def get_revenue_ideas(genre: str) -> list[dict]:
    """pro2 템플릿 기반 부가 사업·수익 창출 아이디어."""
    ideas = [dict(category=g["category"], ideas=list(g["ideas"])) for g in REVENUE_IDEAS_PRO2]
    if "푸드" in genre:
        ideas[0]["ideas"].append("미식 팝업 레스토랑·레시피 키트 정기구독 연계")
    elif "서바이벌" in genre:
        ideas[2]["ideas"].append("모바일 미니게임·보드게임 라이선싱")
    elif "리얼리티" in genre or "캠핑" in genre:
        ideas[0]["ideas"].append("캠핑장·숙박 제휴 체험 패키지")
    return ideas
