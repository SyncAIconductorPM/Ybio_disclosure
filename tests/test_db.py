"""
tests/test_db.py – 실무용 로컬 SQLite DB CRUD 및 정밀 검색 단위 테스트
"""

from api.db import init_db, save_disclosure_record, search_disclosures_db


def test_init_and_save_disclosure():
    """DB 초기화 및 레코드 저장 검증"""
    init_db()
    data = {
        "doc_id": "TEST-DISC-2026-001",
        "filename": "테스트 이사회 의결서.docx",
        "event": "주주총회소집공고",
        "title": "제15기 정기주주총회 소집공고",
        "reporter": "(주)와이바이오로직스",
        "date": "2026-08-05",
        "complete_date": "2026-08-25",
        "amount": "0",
        "counterparty": "주주 전체",
        "status": "ai-mapping",
    }
    doc_id = save_disclosure_record(data)
    assert doc_id == "TEST-DISC-2026-001"


def test_search_disclosures_db():
    """키워드 검색 검증"""
    results = search_disclosures_db(query="주주총회")
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "주주총회" in results[0]["title"] or "주주총회" in results[0]["event"]
