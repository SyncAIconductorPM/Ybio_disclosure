"""
tests/test_browser_service.py – BrowserSessionManager 및 보안 팝업 자동 디스미스 단위 테스트
"""

from api.services.browser_service import BrowserSessionManager


def test_should_auto_close_popup():
    """INISAFE, 8단계 안내 팝업 URL 자동 디스미스 검증"""
    mgr = BrowserSessionManager()

    assert mgr.should_auto_close_popup("https://filing.krx.co.kr/popup/inisafe_install.jsp") is True
    assert mgr.should_auto_close_popup("https://filing.krx.co.kr/notice/submission_step_notice.jsp") is True
    assert mgr.should_auto_close_popup("https://filing.krx.co.kr/main.jsp") is False


def test_auto_dismiss_urls_list():
    """자동 디스미스 화이트리스트 목록 조회 테스트"""
    mgr = BrowserSessionManager()
    urls = mgr.get_auto_dismiss_urls()
    assert "inisafe" in urls
    assert "submission_step_notice" in urls
