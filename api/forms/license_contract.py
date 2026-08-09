"""
api/forms/license_contract.py – 주요사항보고서 (단일판매·공급계약 / 기술이전) Pydantic 모델
"""

from typing import Optional
from pydantic import Field, field_validator

from api.forms.base_form import BaseDisclosureForm


class LicenseContractForm(BaseDisclosureForm):
    """단일판매 공급계약 및 기술이전(License-Out) 주요사항보고서 검증 모델"""

    amount: float = Field(..., gt=0, description="총 계약 금액 (원)")
    counterparty: str = Field(..., description="계약 거래 상대방 회사명")
    upfront_fee: Optional[float] = Field(None, ge=0, description="계약금 (Upfront Fee)")
    recent_revenue: Optional[float] = Field(None, gt=0, description="최근 매출액 (원)")

    @field_validator("counterparty")
    @classmethod
    def validate_counterparty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("거래 상대방 정보는 필수입니다.")
        return v.strip()
