"""신규 기획 분석 엔진 — 로그라인·SWOT·수익 아이디어 (가상 방송 카탈로그 없음)."""

from __future__ import annotations

import random

import numpy as np

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


def _build_logline(title: str, genre: str, cast_list: list[str]) -> str:
    cast_text = ", ".join(cast_list[:2]) if cast_list and cast_list != ["미정"] else "출연진"
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
        f"{slot} 동시간대 경쟁 강도(평균 시청률 {avg_comp:.3f}%)로 진입 장벽이 존재",
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
    buzz = int(round(min(10, (cast_score + format_score) / 2 + random.uniform(-0.3, 0.5))))
    originality = int(round(min(10, format_score + random.uniform(-0.8, 0.8))))
    mass = int(round(min(10, (cast_score + competition_score) / 2 + random.uniform(-0.4, 0.6))))
    feasibility = int(round(min(10, 6.5 + random.uniform(-0.5, 1.5))))
    scalability = int(round(min(10, (buzz + originality) / 2 + random.uniform(-0.3, 0.7))))

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


def get_revenue_ideas(genre: str) -> list[dict]:
    ideas = [dict(category=g["category"], ideas=list(g["ideas"])) for g in REVENUE_IDEAS_PRO2]
    if "푸드" in genre:
        ideas[0]["ideas"].append("미식 팝업 레스토랑·레시피 키트 정기구독 연계")
    elif "서바이벌" in genre:
        ideas[2]["ideas"].append("모바일 미니게임·보드게임 라이선싱")
    elif "리얼리티" in genre or "캠핑" in genre:
        ideas[0]["ideas"].append("캠핑장·숙박 제휴 체험 패키지")
    return ideas
