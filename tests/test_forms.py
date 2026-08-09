"""
tests/test_forms.py – 양식별 Pydantic 검증 모델 단위 테스트
"""

import pytest
from api.forms import get_form_model
from api.forms.shareholder_meeting import ShareholderMeetingForm
from api.forms.stock_option import StockOptionForm
from api.forms.officer_ownership import OfficerOwnershipForm
from api.forms.license_contract import LicenseContractForm


def test_shareholder_meeting_form_valid():
    """정상 주주총회소집공고 검증 테스트"""
    data = {
        "event": "주주총회소집공고",
        "reporter": "(주)와이바이오로직스",
        "title": "제15기 정기주주총회 소집공고",
        "date": "2026-08-05",
        "meeting_type": "정기주주총회",
        "meeting_date": "2026-08-25",
        "meeting_location": "본사 대회의실",
    }
    form = ShareholderMeetingForm(**data)
    assert form.meeting_type == "정기주주총회"
    assert form.meeting_date == "2026-08-25"


def test_shareholder_meeting_form_invalid_date_logic():
    """개최일이 이사회 결의일보다 빠른 경우 검증 실패 테스트"""
    data = {
        "event": "주주총회소집공고",
        "reporter": "(주)와이바이오로직스",
        "title": "제15기 정기주주총회 소집공고",
        "date": "2026-08-25",
        "meeting_date": "2026-08-05",  # 이사회 결의일보다 빠름
        "meeting_location": "본사 대회의실",
    }
    with pytest.raises(ValueError) as exc_info:
        ShareholderMeetingForm(**data)
    assert "빠를 수 없습니다" in str(exc_info.value)


def test_stock_option_form_valid():
    """정상 주식매수선택권 부여 신고 테스트"""
    data = {
        "event": "주식매수선택권 부여에 관한 신고",
        "reporter": "(주)와이바이오로직스",
        "title": "스톡옵션 부여 신고",
        "date": "2026-08-08",
        "common_stock_count": 150000,
        "total_issued_shares": 13500000,
        "exercise_price": 12500,
        "exercise_start_date": "2028-08-09",
        "exercise_end_date": "2033-08-08",
    }
    form = StockOptionForm(**data)
    assert form.common_stock_count == 150000


def test_stock_option_form_exceed_total_shares():
    """부여 주식수가 발행주식총수를 초과 시 실패 테스트"""
    data = {
        "event": "주식매수선택권 부여에 관한 신고",
        "reporter": "(주)와이바이오로직스",
        "title": "스톡옵션 부여 신고",
        "date": "2026-08-08",
        "common_stock_count": 20000000,  # 초과
        "total_issued_shares": 13500000,
        "exercise_price": 12500,
        "exercise_start_date": "2028-08-09",
        "exercise_end_date": "2033-08-08",
    }
    with pytest.raises(ValueError) as exc_info:
        StockOptionForm(**data)
    assert "초과할 수 없습니다" in str(exc_info.value)


def test_get_form_model_registry():
    """서식명 기반 레지스트리 모델 검색 테스트"""
    cls1 = get_form_model("주주총회소집공고")
    assert cls1 == ShareholderMeetingForm

    cls2 = get_form_model("주식매수선택권")
    assert cls2 == StockOptionForm
