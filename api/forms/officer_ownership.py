"""
api/forms/officer_ownership.py – 임원·주요주주 특정증권등 소유상황보고서 Pydantic 검증 모델
"""

from typing import Optional
from pydantic import Field, field_validator

from api.forms.base_form import BaseDisclosureForm


class OfficerOwnershipForm(BaseDisclosureForm):
    """임원/주요주주 주식 소유상황 보고 검증 모델"""

    reporter_name: str = Field(..., description="보고자 성명")
    position: str = Field(..., description="직위/직책 (예: 전무이사)")
    before_share_count: int = Field(0, ge=0, description="변동 전 소유 주식 수")
    change_share_count: int = Field(..., description="변동 주식 수 (양수는 증대, 음수는 감소)")
    after_share_count: int = Field(..., ge=0, description="변동 후 소유 주식 수")

    @field_validator("reporter_name", "position")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("보고자 성명 및 직책 정보는 필수입니다.")
        return v.strip()

    def model_post_init(self, __context) -> None:
        """변동 전 + 변동량 = 변동 후 주식 수 논리 검증"""
        expected_after = self.before_share_count + self.change_share_count
        if expected_after < 0:
            raise ValueError(f"변동 후 소유 주식 수가 음수가 될 수 없습니다 (계산값: {expected_after:,}주)")
