"""업로드 기획안 문서 텍스트 추출 및 필드 검증."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field


REQUIRED_FIELDS = ("title", "genre", "channel", "slot", "cast", "logline")

FIELD_LABELS = {
    "title": "콘텐츠명",
    "genre": "장르",
    "channel": "편성채널",
    "slot": "편성시간",
    "cast": "주요출연자",
    "logline": "로그라인",
}

GENRE_KEYWORDS = {
    "푸드": "푸드 예능",
    "미식": "푸드 예능",
    "요리": "푸드 예능",
    "서바이벌": "서바이벌 예능",
    "퀴즈": "퀴즈 예능",
    "캠핑": "리얼리티 예능",
    "리얼리티": "리얼리티 예능",
    "리얼": "리얼리티 예능",
    "다큐": "리얼리티 예능",
    "스포일러": "리얼리티 예능",
    "코미디": "코미디 예능",
    "웃음": "코미디 예능",
}


@dataclass
class ProposalExtraction:
    title: str = "미정"
    genre: str = "미정"
    channel: str = "ENA"
    slot: str = "미정"
    cast: str = "미정"
    logline: str = "미정"
    intent: str = ""
    raw_text: str = ""
    source_file: str = ""
    drm_locked: bool = False
    extractable: bool = False
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "genre": self.genre,
            "channel": self.channel,
            "slot": self.slot,
            "cast": self.cast,
            "logline": self.logline,
            "intent": self.intent,
            "raw_text": self.raw_text[:4000],
            "source_file": self.source_file,
            "drm_locked": self.drm_locked,
            "extractable": self.extractable,
            "missing_fields": list(self.missing_fields),
            "warnings": list(self.warnings),
        }


def is_drm_pdf(file_bytes: bytes) -> bool:
    return bool(file_bytes) and file_bytes[:5] == b"SCDSA"


def extract_text_from_upload(filename: str, file_bytes: bytes) -> tuple[str, list[str]]:
    """파일 바이트에서 텍스트 추출. (text, warnings)"""
    warnings: list[str] = []
    if not file_bytes:
        return "", ["업로드 파일 내용이 비어 있습니다."]

    if is_drm_pdf(file_bytes):
        return "", [
            "SoftCamp DRM(암호화) PDF라 본문 텍스트를 읽을 수 없습니다. "
            "암호 해제본(일반 PDF/DOCX/TXT)을 업로드하거나 직접 작성 탭을 이용해 주세요."
        ]

    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(file_bytes))
            parts = [(page.extract_text() or "") for page in reader.pages]
            text = "\n".join(parts).strip()
            if not text:
                warnings.append("PDF에서 텍스트를 추출하지 못했습니다. 스캔본이면 OCR 필요 또는 DOCX/TXT로 재업로드해 주세요.")
            return text, warnings

        if name.endswith(".docx"):
            from docx import Document

            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text and p.text.strip())
            if not text:
                warnings.append("DOCX에서 본문 문단을 찾지 못했습니다.")
            return text, warnings

        if name.endswith(".txt") or name.endswith(".md"):
            for enc in ("utf-8", "cp949", "euc-kr"):
                try:
                    return file_bytes.decode(enc).strip(), warnings
                except UnicodeDecodeError:
                    continue
            return file_bytes.decode("utf-8", errors="ignore").strip(), warnings

        warnings.append("지원하지 않는 확장자입니다. PDF/DOCX/TXT/MD만 지원합니다.")
        return "", warnings
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"문서 파싱 중 오류: {exc}")
        return "", warnings


def _first_match(patterns: list[str], text: str) -> str:
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            val = m.group(1).strip()
            val = re.split(r"[\n\r]", val)[0].strip(" -:·")
            if val:
                return val
    return ""


def _guess_genre(text: str, filename: str) -> str:
    blob = f"{filename}\n{text}"
    for keyword, mapped in GENRE_KEYWORDS.items():
        if keyword in blob:
            return mapped
    return ""


def _guess_slot(text: str) -> str:
    labeled = _first_match(
        [
            r"편성\s*(?:시간|일시|요일)?\s*[:：]\s*([월화수목금토일]\s*\d{1,2}\s*[:：]\s*\d{2})",
            r"편성\s*(?:시간|일시|요일)?\s*[:：]\s*([^\n\r]+)",
        ],
        text,
    )
    if labeled:
        m = re.search(r"([월화수목금토일])\s*(\d{1,2})\s*[:：]\s*(\d{2})", labeled)
        if m:
            return f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}"
        return labeled[:40]

    m = re.search(r"([월화수목금토일])\s*(\d{1,2})\s*[:：]\s*(\d{2})", text)
    if m:
        return f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}"
    return ""


def _guess_channel(text: str) -> str:
    labeled = _first_match(
        [r"편성\s*채널\s*[:：]\s*([^\n\r]+)", r"채널\s*[:：]\s*([^\n\r]+)"],
        text,
    )
    if labeled:
        return labeled
    if re.search(r"\bENA\b", text, flags=re.IGNORECASE):
        return "ENA"
    return ""


def _guess_title(text: str, filename: str) -> str:
    labeled = _first_match(
        [
            r"(?:프로그램|콘텐츠|작품)\s*명\s*[:：]\s*([^\n\r]+)",
            r"가칭\s*[:：]\s*([^\n\r]+)",
            r"제목\s*[:：]\s*([^\n\r]+)",
            r"Working\s*Title\s*[:：]\s*([^\n\r]+)",
        ],
        text,
    )
    if labeled:
        return labeled

    name = re.sub(r"\.[^.]+$", "", filename or "")
    name = re.sub(r"\[.*?\]", " ", name)
    name = re.sub(r"(제작\s*)?기획안", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"BM\s*추가", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"[_\\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    # 파일명이 깨진 경우(언더스코어만)는 무시
    if name and not re.fullmatch(r"[_\W\d]+", name) and len(re.findall(r"[가-힣A-Za-z]", name)) >= 2:
        return name
    return ""


def _guess_cast(text: str) -> str:
    labeled = _first_match(
        [
            r"주요\s*출연(?:진|자)?\s*[:：]\s*([^\n\r]+)",
            r"출연(?:진|자)?\s*[:：]\s*([^\n\r]+)",
            r"캐스팅\s*[:：]\s*([^\n\r]+)",
            r"MC\s*[:：]\s*([^\n\r]+)",
        ],
        text,
    )
    if not labeled:
        return ""
    # 플레이스홀더성 값 제거
    if "기획안 추출" in labeled or labeled.strip() in {"미정", "-", "TBD", "tbd"}:
        return ""
    return labeled


def _guess_logline(text: str) -> str:
    labeled = _first_match(
        [
            r"로그\s*라인\s*[:：]\s*([^\n\r]+)",
            r"한\s*줄\s*소개\s*[:：]\s*([^\n\r]+)",
            r"프로그램\s*소개\s*[:：]\s*([^\n\r]+)",
            r"시놉시스\s*[:：]\s*([^\n\r]+)",
        ],
        text,
    )
    if labeled:
        return labeled

    # 기획의도 문단에서 1~2문장 추출
    intent = _first_match(
        [
            r"기획\s*의도\s*[:：]\s*([^\n\r]+)",
            r"기획\s*배경\s*[:：]\s*([^\n\r]+)",
            r"콘셉트\s*[:：]\s*([^\n\r]+)",
        ],
        text,
    )
    if intent:
        return intent

    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 25]
    for ln in lines[:12]:
        if any(k in ln for k in ("예능", "리얼", "출연", "미션", "방송", "프로그램")):
            return ln[:180]
    return lines[0][:180] if lines else ""


def _guess_intent(text: str, logline: str, title: str, genre: str) -> str:
    intent = _first_match(
        [
            r"기획\s*의도\s*[:：]\s*([^\n\r]+)",
            r"기획\s*배경\s*[:：]\s*([^\n\r]+)",
            r"핵심\s*메시지\s*[:：]\s*([^\n\r]+)",
        ],
        text,
    )
    if intent:
        return intent
    if logline and logline != "미정":
        return f"'{title}' 기획안은 {genre} 포맷으로, {logline}"
    return ""


def validate_fields(data: dict) -> list[str]:
    missing = []
    for key in REQUIRED_FIELDS:
        val = str(data.get(key, "")).strip()
        if not val or val == "미정" or "기획안 추출" in val:
            missing.append(FIELD_LABELS[key])
    return missing


def parse_proposal_document(filename: str, file_bytes: bytes | None = None) -> ProposalExtraction:
    """기획안 문서를 세밀 분석해 개요 필드를 추출·검증."""
    result = ProposalExtraction(source_file=filename or "")
    file_bytes = file_bytes or b""

    if is_drm_pdf(file_bytes):
        result.drm_locked = True
        result.warnings.append(
            "첨부 기획안이 SoftCamp DRM으로 암호화되어 본문 분석이 불가합니다. "
            "해제본을 업로드하면 콘텐츠명·출연자·로그라인 등을 정확히 추출합니다."
        )

    text, warn = extract_text_from_upload(filename or "", file_bytes)
    result.warnings.extend(warn)
    result.raw_text = text
    result.extractable = bool(text.strip())

    title = _guess_title(text, filename or "")
    genre = _guess_genre(text, filename or "")
    channel = _guess_channel(text) or ("ENA" if title or genre else "")
    slot = _guess_slot(text)
    cast = _guess_cast(text)
    logline = _guess_logline(text)

    result.title = title or "미정"
    result.genre = genre or "미정"
    result.channel = channel or "미정"
    result.slot = slot or "미정"
    result.cast = cast or "미정"
    result.logline = logline or "미정"
    result.intent = _guess_intent(text, result.logline, result.title, result.genre)
    result.missing_fields = validate_fields(result.to_dict())

    if result.extractable and result.missing_fields:
        result.warnings.append(
            "본문에서 일부 필수 정보가 확인되지 않았습니다: "
            + ", ".join(result.missing_fields)
            + " (해당 항목은 '미정'으로 표기)"
        )
    elif not result.extractable and not result.drm_locked:
        result.warnings.append("문서 본문을 읽지 못해 개요 정보가 미정일 수 있습니다.")

    return result
