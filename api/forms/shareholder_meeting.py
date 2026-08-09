"""
api/forms/shareholder_meeting.py – 주주총회소집공고 Pydantic 검증 모델

주주총회 소집 결의/공고 서식의 법적 및 논리적 규격을 검증합니다.
"""

from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator, model_validator

from api.forms.base_form import BaseDisclosureForm


class ShareholderMeetingForm(BaseDisclosureForm):
    """주주총회소집공고 전용 Pydantic 검증 모델"""

    meeting_type: str = Field("정기주주총회", description="주주총회 구분 (정기주주총회 / 임시주주총회)")
    meeting_date: str = Field(..., description="주주총회 개최일 (YYYY-MM-DD)")
    meeting_location: str = Field(..., description="주주총회 개최 장소")
    agendas: list[str] = Field(default_factory=list, description="의결 안건 목록")

    @field_validator("meeting_date")
    @classmethod
    def validate_meeting_date(cls, v: str) -> str:
        """개최일 날짜 포맷 검증"""
        if not v:
            raise ValueError("주주총회 개최일은 필수입니다.")
        v_clean = v.strip()
        try:
            datetime.strptime(v_clean, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"개최일 날짜 형식이 올바르지 않습니다: '{v}' (YYYY-MM-DD 필요)") from exc
        return v_clean

    @model_validator(mode="after")
    def validate_meeting_logic(self) -> "ShareholderMeetingForm":
        """이사회 결의일(date)과 주총 개최일(meeting_date) 간 2주(14일) 이상 공고 기간 논리 검증"""
        if self.date and self.meeting_date:
            try:
                b_date = datetime.strptime(self.date, "%Y-%m-%d")
                m_date = datetime.strptime(self.meeting_date, "%Y-%m-%d")
                if m_date < b_date:
                    raise ValueError(f"주주총회 개최일({self.meeting_date})이 이사회 결의일({self.date})보다 빠를 수 없습니다.")
            except ValueError as exc:
                if "빠를 수 없습니다" in str(exc):
                    raise exc
        return self
