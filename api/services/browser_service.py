"""
api/services/browser_service.py – Playwright 세션 관리 및 KIND 포털 자동화 모듈

Linux Chromium 및 KRX 포털 환경에서 macOS UA 스푸핑, 보안 팝업(INISAFE 등) 자동 디스미스,
환경변수 자격증명 보안 입력(fill_secret) 및 세션 잠금 관리를 담당합니다.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from api.config import get_settings

logger = logging.getLogger(__name__)

# 자동 닫기 대상 팝업 URL 부분 문자열
_AUTO_CLOSE_URL_SUBSTRINGS = [
    "inisafe",
    "submission_step_notice",
    "miranda",
]

# macOS User-Agent 스푸핑 (Linux 차단 우회)
_MACOS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BrowserSessionManager:
    """KIND 포털 자동화 및 Playwright 영구 세션 관리자"""

    def __init__(self, profile_dir: Path | None = None):
        self.settings = get_settings()
        self.profile_dir = profile_dir or (Path(__file__).resolve().parent.parent.parent / ".browser_profile")
        self._lock = asyncio.Lock()

    def get_auto_dismiss_urls(self) -> list[str]:
        """자동 닫기 팝업 URL 화이트리스트 반환"""
        return list(_AUTO_CLOSE_URL_SUBSTRINGS)

    async def fill_secret(self, page_or_element: Any, selector: str, secret_key: str) -> bool:
        """
        .env 파일에 정의된 자격증명(KRX_ID, KRX_PW)을 대화 로그 노출 없이 안전하게 입력합니다.

        Args:
            page_or_element: Playwright Page 또는 ElementHandle 객체
            selector: 입력 필드 선택자
            secret_key: "KRX_ID" 또는 "KRX_PW"

        Returns:
            성공 여부 (bool)
        """
        secret_value = ""
        if secret_key.upper() == "KRX_ID":
            secret_value = self.settings.krx_id
        elif secret_key.upper() == "KRX_PW":
            secret_value = self.settings.krx_pw
        else:
            logger.warning("허용되지 않은 시크릿 키 접근 시도: %s", secret_key)
            return False

        if not secret_value:
            logger.error("시크릿 키 '%s'의 설정 값이 존재하지 않습니다.", secret_key)
            return False

        try:
            # Playwright fill 호출 (로그에 secret_value를 출력하지 않음)
            if hasattr(page_or_element, "fill"):
                await page_or_element.fill(selector, secret_value)
                logger.info("보안 필드 입력 성공 (selector=%s, key=%s)", selector, secret_key)
                return True
        except Exception as exc:
            logger.error("보안 필드 입력 중 오류 (selector=%s): %s", selector, exc)
            return False

        return False

    def should_auto_close_popup(self, popup_url: str) -> bool:
        """팝업 URL이 자동 닫기 대상에 해당하는지 판단합니다."""
        if not popup_url:
            return False
        url_lower = popup_url.lower()
        return any(sub in url_lower for sub in _AUTO_CLOSE_URL_SUBSTRINGS)
