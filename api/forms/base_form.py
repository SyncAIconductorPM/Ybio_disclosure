"""
api/forms/base_form.py – 공무 및 공시 서식 데이터 베이스 Pydantic 모델

모든 공시 양식 밸리데이터가 상속받는 공통 베이스 클래스입니다.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class BaseDisclosureForm(BaseModel):
    """모든 공시 서식의 공통 필수 필드 및 유효성 검사 모듈"""

    event: str = Field(..., description="공시 서식 유형 (예: 주요사항보고서)")
    reporter: str = Field(..., description="공시 제출인/회사명 (예: (주)와이바이오로직스)")
    title: str = Field(..., description="공시 보고서 제목")
    date: str = Field(..., description="공시 발생일/이사회 결의일 (YYYY-MM-DD)")
    corp_code: Optional[str] = Field(None, description="OpenDART 고유번호 (8자리)")
    stock_code: Optional[str] = Field(None, description="상장 주식 종목코드 (6자리)")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """YYYY-MM-DD 날짜 형식 및 검증"""
        if not v:
            raise ValueError("날짜 정보는 필수입니다.")
        v_clean = v.strip()
        try:
            datetime.strptime(v_clean, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"날짜 형식이 올바르지 않습니다: '{v}' (YYYY-MM-DD 형태여야 함)") from exc
        return v_clean

    @field_validator("corp_code")
    @classmethod
    def validate_corp_code(cls, v: Optional[str]) -> Optional[str]:
        """8자리 숫자 corp_code 검증"""
        if v is not None and v.strip() != "":
            v_clean = v.strip()
            if not v_clean.isdigit() or len(v_clean) != 8:
                raise ValueError(f"corp_code는 8자리 숫자여야 합니다: '{v}'")
            return v_clean
        return v
