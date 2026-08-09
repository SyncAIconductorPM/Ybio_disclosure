"""
api/forms/__init__.py – 양식별 Pydantic 밸리데이터 레지스트리
"""

from typing import Type
from api.forms.base_form import BaseDisclosureForm
from api.forms.shareholder_meeting import ShareholderMeetingForm
from api.forms.stock_option import StockOptionForm
from api.forms.officer_ownership import OfficerOwnershipForm
from api.forms.license_contract import LicenseContractForm

# 서식명 ↔ Pydantic 모델 매핑 레지스트리
FORM_MODELS: dict[str, Type[BaseDisclosureForm]] = {
    "주주총회소집공고": ShareholderMeetingForm,
    "주주총회소집결의": ShareholderMeetingForm,
    "주식매수선택권 부여에 관한 신고": StockOptionForm,
    "임원ㆍ주요주주 특정증권등 소유상황보고서": OfficerOwnershipForm,
    "주요사항보고서(단일판매·공급계약체결)": LicenseContractForm,
    "단일판매·공급계약체결": LicenseContractForm,
}


def get_form_model(event_name: str) -> Type[BaseDisclosureForm]:
    """공시 서식명에 일치하는 Pydantic 모델 클래스를 반환합니다."""
    for key, model_cls in FORM_MODELS.items():
        if key in event_name or event_name in key:
            return model_cls
    return BaseDisclosureForm
