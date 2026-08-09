"""
tests/test_end_to_end_pipeline.py – 공시문서 초안 작성 4단계 전체 자동화 파이프라인 통합 테스트

[Step 1. 대시보드 (index.html)]
  - 원본 문서/텍스트 수신 파싱 및 DB/세션 기록 준비
[Step 2. 워크스페이스 (workspace.html)]
  - 동적 AI 개체 추출 및 DART 1차/2차 이중 법규 검증 (Pydantic / XML DSD)
[Step 3. 결재함 (approval.html)]
  - 전자결재 품의서 검토 및 승인 상태 DB 저장
[Step 4. 제출/다운로드 (submit.html)]
  - DART/KIND 포털 연동 제출 준비 및 .dsd ZIP 바이너리 빌드 출력
"""

import pytest
from api.db import init_db, save_disclosure_record, search_disclosures_db
from api.forms.shareholder_meeting import ShareholderMeetingForm
from api.forms.stock_option import StockOptionForm
from api.services.dsd_service import build_dsd_in_memory, get_templates_root, list_templates, read_template


def test_step1_dashboard_ingestion_and_db_save():
    """Step 1. 대시보드 공시 현황 수신 및 로컬 DB 영속성 저장 검증"""
    init_db()
    
    draft_data = {
        "doc_id": "DISC-2026-E2E-001",
        "filename": "제15기 정기주주총회 소집공고.pdf",
        "event": "주주총회소집공고",
        "title": "제15기 정기주주총회 소집공고",
        "reporter": "(주)와이바이오로직스",
        "date": "2026-08-05",
        "complete_date": "2026-08-25",
        "amount": "0",
        "counterparty": "주주 전체 (한국거래소 코스닥)",
        "asset_type": "의결권 안건 (재무제표 승인, 이사 선임의 건)",
        "ratio": "-",
        "purpose": "제15기 재무제표 승인 및 신임 이사 선임의 건",
        "status": "in-progress"
    }
    
    saved_doc_id = save_disclosure_record(draft_data)
    assert saved_doc_id == "DISC-2026-E2E-001"
    
    # DB 검색을 통한 수신 확인
    search_res = search_disclosures_db("정기주주총회")
    assert len(search_res) >= 1
    assert any(r["doc_id"] == "DISC-2026-E2E-001" for r in search_res)



def test_step2_workspace_validation_rules():
    """Step 2. 워크스페이스 법규 & DART XML 이중 밸리데이션 검증"""
    # 1. Pydantic 비즈니스 검증 (이사회 결의일 <= 주총 개최일)
    valid_form = ShareholderMeetingForm(
        event="주주총회소집공고",
        reporter="(주)와이바이오로직스",
        title="제15기 정기주주총회 소집공고",
        date="2026-08-05",
        meeting_date="2026-08-25",
        meeting_type="정기주주총회",
        meeting_location="서울특별시 강남구 본사 9층 강당",
        agendas=["제15기 재무제표 승인", "이사 선임의 건"]
    )
    assert valid_form.meeting_type == "정기주주총회"

    # 날짜 논리 오류 검사 (주총 개최일이 결의일보다 앞선 경우)
    with pytest.raises(ValueError):
        ShareholderMeetingForm(
            event="주주총회소집공고",
            reporter="(주)와이바이오로직스",
            title="잘못된 날짜 공시",
            date="2026-08-25",
            meeting_date="2026-08-05", # 오류!
            meeting_type="정기주주총회",
            meeting_location="본사",
            agendas=["안건"]
        )

    # 2. DSD 템플릿 탐색 검증
    templates = list_templates()
    assert len(templates) > 0



def test_step3_approval_flow_and_signature():
    """Step 3. 결재함 전자결재 검토 및 최종 승인 상태 업데이트"""
    approval_record = {
        "doc_id": "DISC-2026-E2E-001",
        "filename": "제15기 정기주주총회 소집공고.pdf",
        "event": "주주총회소집공고",
        "title": "제15기 정기주주총회 소집공고",
        "reporter": "(주)와이바이오로직스",
        "date": "2026-08-05",
        "complete_date": "2026-08-25",
        "amount": "0",
        "counterparty": "주주 전체",
        "status": "approved" # 승인 완료
    }
    doc_id = save_disclosure_record(approval_record)
    assert doc_id == "DISC-2026-E2E-001"
    
    # 승인 완료 상태 조회 검증
    db_record = search_disclosures_db("DISC-2026-E2E-001")[0]
    assert db_record["status"] == "approved"


def test_step4_submit_dsd_binary_generation():
    """Step 4. 제출/다운로드 단계에서 .dsd 바이너리 파일 빌드 검증"""
    contents_xml = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT>
  <TITLE>제15기 정기주주총회 소집공고</TITLE>
  <BODY>
    <TR><TE>2026-08-05</TE><TE>2026-08-25</TE></TR>
  </BODY>
</DOCUMENT>"""

    meta_xml = """<?xml version="1.0" encoding="utf-8"?>
<META>
  <REPORTER>YBiologics</REPORTER>
  <FORM_CODE>00591</FORM_CODE>
</META>"""

    # .dsd 바이너리 빌드 테스트
    dsd_bytes = build_dsd_in_memory(
        contents_xml=contents_xml,
        meta_xml=meta_xml,
        strict_validation=False
    )
    assert isinstance(dsd_bytes, bytes)
    assert len(dsd_bytes) > 0
    assert dsd_bytes[:2] == b'PK' # ZIP 헤더 확인
