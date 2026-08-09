"""
api/routers/system.py – 시스템 환경변수 및 OpenDART/KRX 연동 상태 라우터
.env 파일에 정의된 API 키 및 KRX 접속 세션 정보의 연동 상태를 제공합니다.
"""

import logging
from fastapi import APIRouter, status
from pydantic import BaseModel

from api.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System Config"])


class ConfigStatusResponse(BaseModel):
    """.env 환경변수 연동 상태 스키마"""
    opendart_connected: bool
    opendart_key_masked: str
    krx_connected: bool
    krx_url: str
    krx_id: str
    gemini_model: str
    company_name: str
    stock_code: str


@router.get(
    "/config-status",
    response_model=ConfigStatusResponse,
    status_code=status.HTTP_200_OK,
    summary=".env 환경변수 및 시스템 연동 상태 조회",
    description=".env에 설정된 OpenDART API Key, KRX 계정, Gemini AI 모델 연동 상태를 확인합니다.",
)
async def get_config_status() -> ConfigStatusResponse:
    """.env 환경 변수 실시간 로드 및 마스킹된 정보 반환"""
    try:
        settings = get_settings()
        
        # OpenDART 마스킹 키 생성
        raw_dart_key = settings.opendart_api_key or ""
        masked_dart_key = f"{raw_dart_key[:8]}...{raw_dart_key[-8:]}" if len(raw_dart_key) > 16 else "UNCONFIGURED"

        return ConfigStatusResponse(
            opendart_connected=bool(settings.opendart_api_key),
            opendart_key_masked=masked_dart_key,
            krx_connected=bool(settings.krx_id and settings.krx_pw),
            krx_url=settings.krx_url,
            krx_id=settings.krx_id or "ybiologics",
            gemini_model=settings.gemini_model,
            company_name="(주)와이바이오로직스",
            stock_code="338840",
        )
    except Exception as exc:
        logger.error("시스템 설정 상태 로드 중 오류 발생: %s", exc)
        return ConfigStatusResponse(
            opendart_connected=False,
            opendart_key_masked="ERROR",
            krx_connected=False,
            krx_url="https://filing.krx.co.kr/",
            krx_id="ybiologics",
            gemini_model="gemini-1.5-pro",
            company_name="(주)와이바이오로직스",
            stock_code="338840",
        )
