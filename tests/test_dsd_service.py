"""
tests/test_dsd_service.py – DSD 서비스 모듈 단위 테스트 (pytest)

.dsd 파서, DART XML 규격 유효성 검증엔진, 메모리 캐싱 및 바이너리 빌더 기능 검증.
"""

import zipfile
import pytest
from pathlib import Path

from api.services.dsd_service import (
    DartValidationError,
    build_dsd_in_memory,
    extract_document_name,
    find_empty_template_by_name,
    get_templates_root,
    list_templates,
    read_template,
    sanitize_filename,
    validate_against_template,
)

# ── 테스트용 샘플 XML ──────────────────────────────────────────────────

VALID_EMPTY_XML = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT>
    <DOCUMENT-NAME>주주총회소집공고</DOCUMENT-NAME>
    <TABLE-GROUP ACLASS="standard">
        <TBODY>
            <TR>
                <TE ACODE="A101">테스트 내용</TE>
                <TU AUNIT="U001" AUNITVALUE="KRW">1000</TU>
            </TR>
        </TBODY>
    </TABLE-GROUP>
</DOCUMENT>"""

VALID_FILLED_XML = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT>
    <DOCUMENT-NAME>주주총회소집공고</DOCUMENT-NAME>
    <TABLE-GROUP ACLASS="standard">
        <TBODY>
            <TR>
                <TE ACODE="A101">수정된 주주총회 내용</TE>
                <TU AUNIT="U001" AUNITVALUE="KRW">5000</TU>
            </TR>
        </TBODY>
    </TABLE-GROUP>
</DOCUMENT>"""

INVALID_EMPTY_CELL_XML = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT>
    <DOCUMENT-NAME>주주총회소집공고</DOCUMENT-NAME>
    <TABLE-GROUP ACLASS="standard">
        <TBODY>
            <TR>
                <TE ACODE="A101"></TE>
                <TU AUNIT="U001" AUNITVALUE="KRW">1000</TU>
            </TR>
        </TBODY>
    </TABLE-GROUP>
</DOCUMENT>"""

INVALID_DROPPED_ROW_XML = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT>
    <DOCUMENT-NAME>주주총회소집공고</DOCUMENT-NAME>
    <TABLE-GROUP ACLASS="standard">
        <TBODY>
        </TBODY>
    </TABLE-GROUP>
</DOCUMENT>"""

VALID_META_XML = """<?xml version="1.0" encoding="utf-8"?>
<META>
    <FILE-INFO>
        <CREATOR>YBioLogics Auto</CREATOR>
    </FILE-INFO>
</META>"""


def test_sanitize_filename():
    """파일명 정화 테스트."""
    assert sanitize_filename("사업보고서?.dsd") == "사업보고서_.dsd"
    assert sanitize_filename("  test doc  ") == "test doc.dsd"



def test_extract_document_name():
    """문서명 추출 테스트."""
    doc_name = extract_document_name(VALID_EMPTY_XML)
    assert doc_name == "주주총회소집공고"


def test_validate_against_template_success():
    """정상 XML 2차 스키마 검증 통과 테스트."""
    errors = validate_against_template(VALID_FILLED_XML, VALID_EMPTY_XML)
    assert len(errors) == 0


def test_validate_against_template_empty_cell_fail():
    """빈 셀 누락 시 에러 감지 테스트."""
    errors = validate_against_template(INVALID_EMPTY_CELL_XML, VALID_EMPTY_XML)
    assert len(errors) > 0
    assert any("빈 셀 누락" in err for err in errors)


def test_validate_against_template_dropped_row_fail():
    """TR 행 삭제 시 DART 규격 위반 감지 테스트."""
    errors = validate_against_template(INVALID_DROPPED_ROW_XML, VALID_EMPTY_XML)
    assert len(errors) > 0
    assert any("행 삭제 오류" in err for err in errors)


def test_build_dsd_in_memory_success():
    """메모리 바이너리 빌드 및 ZIP 해제 검증 테스트."""
    dsd_bytes = build_dsd_in_memory(
        contents_xml=VALID_FILLED_XML,
        meta_xml=VALID_META_XML,
        empty_xml=VALID_EMPTY_XML,
        strict_validation=True,
    )
    assert len(dsd_bytes) > 0

    # ZIP 바이너리 무결성 검증
    import io
    with zipfile.ZipFile(io.BytesIO(dsd_bytes), "r") as z:
        names = set(z.namelist())
        assert "contents.xml" in names
        assert "meta.xml" in names


def test_build_dsd_in_memory_validation_error():
    """규격 위반 시 DartValidationError 예외 발생 테스트."""
    with pytest.raises(DartValidationError) as exc_info:
        build_dsd_in_memory(
            contents_xml=INVALID_EMPTY_CELL_XML,
            meta_xml=VALID_META_XML,
            empty_xml=VALID_EMPTY_XML,
            strict_validation=True,
        )
    assert "DART 편집기 규격 오류" in str(exc_info.value)


def test_list_templates_and_find():
    """실제 템플릿 파일 스캔 및 검색 테스트."""
    root = get_templates_root()
    if root.exists():
        templates = list_templates()
        assert isinstance(templates, list)
        
        found = find_empty_template_by_name("사업보고서")
        if found:
            assert found.is_file()
