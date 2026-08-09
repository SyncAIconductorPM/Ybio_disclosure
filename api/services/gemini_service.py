"""
api/services/gemini_service.py – Google Gemini AI 서비스
업로드된 문서 텍스트를 분석하여 공시 필드를 추출하고 YAML을 생성합니다.

규칙: 에러 처리 포함, API 키 하드코딩 금지
"""

import json
import logging
from typing import Any

import google.generativeai as genai

from api.config import get_settings

logger = logging.getLogger(__name__)


def _get_client() -> genai.GenerativeModel:
    """Gemini 모델 클라이언트를 초기화하여 반환합니다."""
    settings = get_settings()
    genai.configure(api_key=settings.google_api_key)

    # .env의 모델명을 우선 시도, 실패 시 안정 버전으로 fallback
    try:
        model = genai.GenerativeModel(settings.gemini_model)
        return model
    except Exception:
        logger.warning(
            "모델 '%s' 초기화 실패 → gemini-1.5-pro로 대체합니다.",
            settings.gemini_model,
        )
        return genai.GenerativeModel("gemini-1.5-pro")


# ── 필드 추출 프롬프트 ────────────────────────────────────────────────
_EXTRACT_PROMPT_TEMPLATE = """
당신은 한국 공시 전문 AI입니다. 아래 문서에서 공시에 필요한 핵심 필드를 추출하여
반드시 유효한 JSON 객체만 응답하세요 (마크다운 코드 블록 없이 순수 JSON).

추출할 필드:
- event: 공시 유형 (예: "주요사항보고", "분기보고서", "주주총회소집결의")
- counterparty: 거래 상대방 회사명 (없으면 null)
- amount: 거래금액 (원화 숫자, 없으면 null)
- date: 이사회 결의일 또는 주요 날짜 (YYYY-MM-DD, 없으면 null)
- reporter: 제출 회사명
- title: 공시 제목
- purpose: 거래 목적 또는 주요 내용 (2~3문장)
- asset_type: 자산 유형 (해당 없으면 null)
- ratio: 자산 총액 대비 비율 (예: "5.2%", 없으면 null)

문서 내용:
\"\"\"
{document_text}
\"\"\"

JSON만 응답 (추가 설명 없음):
"""

# ── 초안 생성 프롬프트 ────────────────────────────────────────────────
_DRAFT_PROMPT_TEMPLATE = """
당신은 한국 DART/KIND 공시 전문가입니다. 아래 YAML 데이터를 바탕으로
한국어 공시 초안 문서의 "주요 내용" 섹션을 작성하세요.

규칙:
1. 금융감독원 공시 양식에 맞는 공식 문어체 사용
2. 숫자는 천 단위 구분자 포함 (예: 3,000,000,000)
3. 날짜는 YYYY년 M월 D일 형식
4. 200자 이내

YAML 데이터:
{yaml_data}

초안 내용만 응답 (추가 설명 없음):
"""


async def extract_fields(document_text: str) -> dict[str, Any]:
    """
    문서 텍스트에서 공시 필드를 추출합니다.

    Args:
        document_text: 파싱된 문서 전문 텍스트

    Returns:
        추출된 필드 딕셔너리

    Raises:
        ValueError: Gemini 응답을 JSON으로 파싱할 수 없을 때
        RuntimeError: Gemini API 호출 실패 시
    """
    if not document_text or not document_text.strip():
        raise ValueError("문서 텍스트가 비어 있습니다.")

    # 텍스트 길이 제한 (토큰 과다 방지)
    max_chars = 8000
    trimmed = document_text[:max_chars]
    if len(document_text) > max_chars:
        logger.info("문서 텍스트를 %d자로 자릅니다 (원본: %d자).", max_chars, len(document_text))

    prompt = _EXTRACT_PROMPT_TEMPLATE.format(document_text=trimmed)

    try:
        model = _get_client()
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # JSON 코드 블록 제거 (모델이 감싸는 경우 대비)
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result: dict[str, Any] = json.loads(raw_text)
        logger.info("Gemini 필드 추출 완료: %s", list(result.keys()))
        return result

    except json.JSONDecodeError as exc:
        logger.error("Gemini 응답 JSON 파싱 실패: %s", exc)
        raise ValueError(f"AI 응답을 파싱할 수 없습니다: {exc}") from exc
    except Exception as exc:
        logger.error("Gemini API 호출 오류: %s", exc)
        raise RuntimeError(f"Gemini API 오류: {exc}") from exc


async def generate_draft_text(yaml_data: dict[str, Any]) -> str:
    """
    추출된 YAML 데이터를 바탕으로 공시 초안 텍스트를 생성합니다.

    Args:
        yaml_data: 추출된 공시 필드 딕셔너리

    Returns:
        한국어 공시 초안 텍스트

    Raises:
        RuntimeError: Gemini API 호출 실패 시
    """
    import yaml as yaml_lib

    yaml_str = yaml_lib.dump(yaml_data, allow_unicode=True, default_flow_style=False)
    prompt = _DRAFT_PROMPT_TEMPLATE.format(yaml_data=yaml_str)

    try:
        model = _get_client()
        response = model.generate_content(prompt)
        draft = response.text.strip()
        logger.info("Gemini 초안 생성 완료 (%d자)", len(draft))
        return draft

    except Exception as exc:
        logger.error("Gemini 초안 생성 오류: %s", exc)
        raise RuntimeError(f"초안 생성 오류: {exc}") from exc
