"""
api/routers/validate.py – 공시 필드 유효성 검증 라우터
POST /validate : YAML/JSON 필드 검증 → 오류 목록 반환
"""

import logging
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.services.dsd_service import (
    find_empty_template_by_name,
    read_template,
    validate_against_template,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/validate", tags=["유효성 검증"])


# ── 스키마 ──────────────────────────────────────────────────────────────


class ValidationError(BaseModel):
    """개별 필드 유효성 오류"""
    field: str
    message: str
    severity: str = "error"  # "error" | "warning"


class ValidationResponse(BaseModel):
    """검증 결과 응답"""
    valid: bool
    error_count: int
    warning_count: int
    errors: list[ValidationError]


class ValidateRequest(BaseModel):
    """검증 요청 바디"""
    fields: dict[str, Any]
    contents_xml: str | None = None
    template_name: str | None = None



# ── 검증 규칙 ────────────────────────────────────────────────────────────

# 필수 필드 목록
REQUIRED_FIELDS = ["event", "reporter", "title"]

# 날짜 형식 (YYYY-MM-DD)
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 비율 형식 (숫자%)
_RATIO_PATTERN = re.compile(r"^\d+(\.\d+)?%$")


def _validate_required(fields: dict, errors: list[ValidationError]) -> None:
    """필수 필드 누락 검사."""
    for field in REQUIRED_FIELDS:
        value = fields.get(field)
        if value is None or str(value).strip() == "":
            errors.append(ValidationError(
                field=field,
                message=f"'{field}'은(는) 필수 항목입니다.",
                severity="error",
            ))


def _validate_date_fields(fields: dict, errors: list[ValidationError]) -> None:
    """날짜 형식 및 논리 검증 (YYYY-MM-DD)."""
    date_fields = ["date", "board_resolution_date", "grant_date",
                   "exercise_start_date", "exercise_end_date"]

    parsed_dates: dict[str, datetime] = {}

    for field in date_fields:
        value = fields.get(field)
        if not value:
            continue
        value_str = str(value).strip()
        if not _DATE_PATTERN.match(value_str):
            errors.append(ValidationError(
                field=field,
                message=f"'{field}' 날짜 형식 오류: '{value_str}' (YYYY-MM-DD 필요)",
                severity="error",
            ))
            continue
        try:
            parsed_dates[field] = datetime.strptime(value_str, "%Y-%m-%d")
        except ValueError:
            errors.append(ValidationError(
                field=field,
                message=f"'{field}' 유효하지 않은 날짜: '{value_str}'",
                severity="error",
            ))

    # 행사기간 논리 검증 (시작 <= 종료)
    start = parsed_dates.get("exercise_start_date")
    end = parsed_dates.get("exercise_end_date")
    if start and end and start > end:
        errors.append(ValidationError(
            field="exercise_end_date",
            message="행사기간 종료일이 시작일보다 빠릅니다.",
            severity="error",
        ))


def _validate_amount_fields(fields: dict, errors: list[ValidationError]) -> None:
    """금액 필드 숫자 단위 검증."""
    amount_fields = ["amount", "common_stock_count", "other_stock_count",
                     "total_common_stock", "total_other_stock"]

    for field in amount_fields:
        value = fields.get(field)
        if value is None:
            continue
        # 콤마 제거 후 숫자 검증
        clean = str(value).replace(",", "").strip()
        if not clean.lstrip("-").isdigit():
            errors.append(ValidationError(
                field=field,
                message=f"'{field}'은(는) 숫자여야 합니다. 현재 값: '{value}'",
                severity="error",
            ))
        elif int(clean.lstrip("-")) < 0:
            errors.append(ValidationError(
                field=field,
                message=f"'{field}'은(는) 0 이상이어야 합니다.",
                severity="warning",
            ))


def _validate_ratio_field(fields: dict, errors: list[ValidationError]) -> None:
    """비율 형식 검증 (예: '5.2%')."""
    ratio = fields.get("ratio")
    if ratio and str(ratio).strip() not in ("-", ""):
        if not _RATIO_PATTERN.match(str(ratio).strip()):
            errors.append(ValidationError(
                field="ratio",
                message=f"비율 형식 오류: '{ratio}' (예: '5.2%')",
                severity="warning",
            ))


def _validate_business_rules(fields: dict, errors: list[ValidationError]) -> None:
    """비즈니스 로직 검증 규칙."""
    # 공시 유형 화이트리스트
    valid_events = [
        "주요사항보고", "분기보고서", "반기보고서", "사업보고서",
        "주주총회소집결의", "주식매수선택권 부여에 관한 신고",
        "임원 선임", "최대주주 변경", "자기주식 취득",
    ]
    event = fields.get("event", "")
    if event and not any(v in str(event) for v in valid_events):
        errors.append(ValidationError(
            field="event",
            message=f"공시 유형 '{event}'을 인식할 수 없습니다. 수동으로 확인하세요.",
            severity="warning",
        ))


# ── 엔드포인트 ──────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ValidationResponse,
    summary="공시 필드 유효성 검증",
    description="추출된 필드 데이터를 검증하여 누락, 형식 오류, 논리 오류를 반환합니다.",
)
async def validate_fields(body: ValidateRequest) -> ValidationResponse:
    """
    공시 필드 유효성 검증.

    검증 항목:
    1. 필수 필드 누락 검사
    2. 날짜 형식 및 논리 검증 (YYYY-MM-DD, 시작 <= 종료)
    3. 금액 숫자 단위 검증
    4. 비율 형식 검증 (예: '5.2%')
    5. 공시 유형 화이트리스트 검증
    """
    if not body.fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="검증할 필드가 없습니다.",
        )

    errors: list[ValidationError] = []

    _validate_required(body.fields, errors)
    _validate_date_fields(body.fields, errors)
    _validate_amount_fields(body.fields, errors)
    _validate_ratio_field(body.fields, errors)
    _validate_business_rules(body.fields, errors)

    # ── Layer-2: DART XML 스키마 2차 검증 ────────────────────────────────
    if body.contents_xml:
        doc_name = body.template_name or body.fields.get("event") or body.fields.get("title")
        if doc_name:
            empty_path = find_empty_template_by_name(str(doc_name))
            if empty_path:
                try:
                    empty_tpl = read_template(empty_path)
                    xml_errors = validate_against_template(body.contents_xml, empty_tpl["contents_xml"])
                    for xml_err in xml_errors:
                        errors.append(ValidationError(
                            field="contents_xml",
                            message=f"[DART 규격 오류] {xml_err}",
                            severity="error",
                        ))
                except Exception as exc:
                    logger.warning("2차 XML 스키마 검증 중 템플릿 읽기 오류: %s", exc)

    error_count   = sum(1 for e in errors if e.severity == "error")
    warning_count = sum(1 for e in errors if e.severity == "warning")

    logger.info(
        "필드 검증 완료: 오류 %d건, 경고 %d건 (총 필드 %d개)",
        error_count,
        warning_count,
        len(body.fields),
    )

    return ValidationResponse(
        valid=error_count == 0,
        error_count=error_count,
        warning_count=warning_count,
        errors=errors,
    )

