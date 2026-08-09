"""
tests/test_mock_disclosures.py – 가상 공시 이슈 데이터 검증 테스트

생성된 가상의 공시 이슈 데이터(기술이전, 주식매수선택권, 임원 소유상황)를 파싱하고
FastAPI 유효성 검증 로직(validate.py) 및 DSD 서비스(dsd_service.py)와 연동하여 
정상적으로 데이터 검증 및 매핑이 수행되는지 테스트합니다.
"""

from pathlib import Path
import pytest
import yaml

from api.config import get_settings
from api.routers.validate import _validate_amount_fields, _validate_date_fields, _validate_required, ValidationError
from api.services.dsd_service import find_empty_template_by_name, get_templates_root


def get_samples_dir() -> Path:
    """samples 디렉토리 경로 반환 (환경변수 설정 지원)."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "samples"


def load_yaml_sample(filename: str) -> dict:
    """
    샘플 YAML 파일을 동적으로 읽어옵니다.

    Args:
        filename: samples 디렉토리 내의 파일명 (예: mock_license_out_contract.yaml)

    Returns:
        파싱된 딕셔너리 객체

    Raises:
        FileNotFoundError: 파일이 존재하지 않는 경우
        ValueError: YAML 파싱 오류 시
    """
    samples_dir = get_samples_dir()
    file_path = samples_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"가상 공시 데이터 파일을 찾을 수 없습니다: '{file_path}'")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"'{filename}' 내의 데이터가 딕셔너리 형식이 아닙니다.")
            return data
    except Exception as exc:
        raise ValueError(f"'{filename}' YAML 로딩 중 오류 발생: {exc}") from exc


def test_mock_license_out_contract():
    """가상 공시 데이터 1: 기술이전(License-Out) 계약 공시 검증."""
    data = load_yaml_sample("mock_license_out_contract.yaml")
    
    assert data["event"] == "주요사항보고서(단일판매·공급계약체결)"
    assert data["reporter"] == "(주)와이바이오로직스"
    assert data["amount"] == 300000000000

    errors: list[ValidationError] = []
    _validate_required(data, errors)
    _validate_date_fields(data, errors)
    _validate_amount_fields(data, errors)

    # 에러가 전혀 없어야 정상
    assert len([e for e in errors if e.severity == "error"]) == 0


def test_mock_stock_option_grant():
    """가상 공시 데이터 2: 주식매수선택권 부여 공시 검증."""
    data = load_yaml_sample("mock_stock_option_grant.yaml")

    assert data["event"] == "주식매수선택권 부여에 관한 신고"
    assert data["common_stock_count"] == 150000
    assert data["exercise_price"] == 12500

    errors: list[ValidationError] = []
    _validate_required(data, errors)
    _validate_date_fields(data, errors)
    _validate_amount_fields(data, errors)

    assert len([e for e in errors if e.severity == "error"]) == 0


def test_mock_officer_stock_ownership():
    """가상 공시 데이터 3: 임원 주식 소유상황 보고 공시 검증."""
    data = load_yaml_sample("mock_officer_stock_ownership.yaml")

    assert data["event"] == "임원·주요주주 특정증권등 소유상황보고서"
    assert data["reporter"] == "김신약"
    assert data["stock_details"]["change_share_count"] == 10000

    errors: list[ValidationError] = []
    _validate_required(data, errors)
    _validate_date_fields(data, errors)

    assert len([e for e in errors if e.severity == "error"]) == 0


def test_find_template_for_mock_disclosures():
    """가상 공시 데이터의 event 유형에 맞는 DSD 템플릿 검색 테스트."""
    doc_name = "주식매수선택권 부여에 관한 신고"
    template_path = find_empty_template_by_name(doc_name)
    
    # 템플릿 파일이 존재하는지 확인
    assert template_path is not None
    assert template_path.is_file()
    assert doc_name in template_path.stem
