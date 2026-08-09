"""
api/services/kind_service.py – KRX KIND 포털 자동화 서비스
Playwright를 사용하여 KIND 포털에 로그인하고 공시 양식을 자동으로 채웁니다.

⚠️ 제약사항:
- KIND는 ActiveX 기반 최종 제출 불가 → 양식 pre-fill까지만 자동화
- 최종 제출은 담당자가 직접 수행 (Human-in-the-loop)

규칙: 에러 처리 포함, 자격증명 하드코딩 금지
"""

import asyncio
import base64
import logging
from typing import Any

from api.config import get_settings

logger = logging.getLogger(__name__)

# Playwright 타임아웃 (ms)
_NAV_TIMEOUT = 30_000
_SELECTOR_TIMEOUT = 10_000


async def prefill_kind_form(
    template_name: str,
    form_data: dict[str, Any],
) -> dict[str, Any]:
    """
    (Mock) KIND 포털 양식 자동 입력을 시뮬레이션합니다.
    (빌드 환경 문제로 Playwright가 제외되었습니다)
    """
    logger.info("KIND 자동 입력 Mock 시작: %s", template_name)
    await asyncio.sleep(2)  # 통신 지연 시뮬레이션

    filled_count = len([v for v in form_data.values() if v])

    # 빈 1x1 투명 PNG
    mock_screenshot = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    return {
        "status": "prefilled",
        "screenshot": f"data:image/png;base64,{mock_screenshot}",
        "message": f"양식 {filled_count}개 필드가 자동 입력되었습니다. (Mock 처리)",
        "filled_count": filled_count,
    }

