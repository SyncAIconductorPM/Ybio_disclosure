"""
api/routers/kind.py – KRX KIND 포털 자동화 라우터
POST /kind/prefill   : KIND 양식 자동 입력
GET  /kind/status    : 서버 Playwright 환경 상태 확인
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.services import kind_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kind", tags=["KIND 포털 자동화"])


# ── 스키마 ────────────────────────────────────────────────────────────────


class PrefillRequest(BaseModel):
    """KIND 양식 자동 입력 요청"""
    template_name: str
    form_data: dict[str, Any]


class PrefillResponse(BaseModel):
    """KIND 양식 자동 입력 결과"""
    status: str            # "prefilled" | "login_failed" | "form_not_found"
    message: str
    screenshot: str | None = None   # base64 PNG Data URL
    filled_count: int = 0


class KindStatusResponse(BaseModel):
    """KIND 자동화 환경 상태"""
    playwright_available: bool
    message: str


# ── 엔드포인트 ────────────────────────────────────────────────────────────


@router.get(
    "/status",
    response_model=KindStatusResponse,
    summary="KIND 자동화 환경 상태 확인",
    description="Playwright 설치 여부 및 KRX 포털 연결 가능 여부를 확인합니다.",
)
async def get_kind_status() -> KindStatusResponse:
    """Playwright 설치 여부를 확인합니다."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            await browser.close()
        return KindStatusResponse(
            playwright_available=True,
            message="Playwright 정상 작동 중입니다.",
        )
    except Exception as exc:
        logger.warning("Playwright 상태 확인 실패: %s", exc)
        return KindStatusResponse(
            playwright_available=False,
            message=f"Playwright를 사용할 수 없습니다: {exc}",
        )


@router.post(
    "/prefill",
    response_model=PrefillResponse,
    summary="KIND 양식 자동 입력",
    description=(
        "Playwright로 KIND 포털에 로그인하고 공시 양식 필드를 자동으로 입력합니다. "
        "⚠️ ActiveX 제약으로 최종 제출은 담당자가 직접 수행해야 합니다."
    ),
)
async def prefill_kind(body: PrefillRequest) -> PrefillResponse:
    """
    KIND 포털 양식 자동 입력.

    처리 흐름:
    1. Playwright로 KIND 포털 접속
    2. 아이디/비밀번호 로그인 (.env 값 사용)
    3. 공시 양식 검색 및 열기
    4. YAML 데이터 기반 필드 자동 입력
    5. 스크린샷 캡처 후 반환

    에러 케이스:
    - 400: 요청 데이터 누락
    - 503: Playwright 또는 KIND 포털 연결 실패
    """
    if not body.template_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="template_name이 비어 있습니다.",
        )

    if not body.form_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="form_data가 비어 있습니다.",
        )

    logger.info(
        "KIND 자동 입력 시작: template='%s', fields=%d개",
        body.template_name,
        len(body.form_data),
    )

    try:
        result = await kind_service.prefill_kind_form(
            template_name=body.template_name,
            form_data=body.form_data,
        )
        return PrefillResponse(
            status=result["status"],
            message=result["message"],
            screenshot=result.get("screenshot"),
            filled_count=result.get("filled_count", 0),
        )
    except RuntimeError as exc:
        logger.error("KIND 자동화 실패: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("KIND 예상치 못한 오류: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"내부 서버 오류: {exc}",
        ) from exc
