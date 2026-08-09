"""
api/forms/stock_option.py – 주식매수선택권 부여에 관한 신고 Pydantic 검증 모델

스톡옵션 부여 수량, 행사가격, 행사기간(시작일 <= 종료일) 등의 한계를 검증합니다.
"""

from datetime import datetime
from pydantic import Field, field_validator, model_validator

from api.forms.base_form import BaseDisclosureForm


class StockOptionForm(BaseDisclosureForm):
    """주식매수선택권 부여 신고 전용 Pydantic 검증 모델"""

    common_stock_count: int = Field(..., ge=0, description="부여 보통주식 수")
    total_issued_shares: int = Field(..., gt=0, description="발행주식 총수")
    exercise_price: float = Field(..., gt=0, description="1주당 행사 가격 (원)")
    exercise_start_date: str = Field(..., description="행사기간 시작일 (YYYY-MM-DD)")
    exercise_end_date: str = Field(..., description="행사기간 종료일 (YYYY-MM-DD)")

    @field_validator("exercise_start_date", "exercise_end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not v:
            raise ValueError("행사기간 날짜는 필수입니다.")
        v_clean = v.strip()
        try:
            datetime.strptime(v_clean, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"행사기간 날짜 형식이 올바르지 않습니다: '{v}' (YYYY-MM-DD 필요)") from exc
        return v_clean

    @model_validator(mode="after")
    def validate_stock_rules(self) -> "StockOptionForm":
        """1) 부여 수량이 발행주식 총수를 초과하지 않는지, 2) 행사 시작일 <= 종료일 검증"""
        if self.common_stock_count > self.total_issued_shares:
            raise ValueError(
                f"부여 보통주식 수({self.common_stock_count:,}주)가 발행주식 총수({self.total_issued_shares:,}주)를 초과할 수 없습니다."
            )

        try:
            s_date = datetime.strptime(self.exercise_start_date, "%Y-%m-%d")
            e_date = datetime.strptime(self.exercise_end_date, "%Y-%m-%d")
            if e_date < s_date:
                raise ValueError(
                    f"행사 종료일({self.exercise_end_date})이 행사 시작일({self.exercise_start_date})보다 빠를 수 없습니다."
                )
        except ValueError as exc:
            if "빠를 수 없습니다" in str(exc):
                raise exc

        return self
