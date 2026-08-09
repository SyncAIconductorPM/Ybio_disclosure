"""
api/db.py – 실무용 공시 자동화 시스템 로컬 SQLite 데이터베이스 연동 모듈

공시 초안, 이력, 승인 상태, AI 분석 로그를 영구 저장하고 
실무자가 과거 공시를 언제든지 검색하고 재활용할 수 있도록 데이터 영속성을 제공합니다.
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, List, Optional, Dict

DB_PATH = Path(__file__).resolve().parent.parent / "disclosure_system.db"


def get_db_connection() -> sqlite3.Connection:
    """SQLite 데이터베이스 연결 객체 반환 (Row 딕셔너리 매핑)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """실무용 공시 이력 및 초안 테이블 자동 생성 및 초기화"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 공시 처리 이력 및 초안 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disclosures (
            id TEXT PRIMARY KEY,
            doc_id TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            event TEXT NOT NULL,
            title TEXT NOT NULL,
            reporter TEXT NOT NULL,
            date TEXT NOT NULL,
            complete_date TEXT,
            amount TEXT,
            counterparty TEXT,
            asset_type TEXT,
            ratio TEXT,
            purpose TEXT,
            status TEXT DEFAULT 'ai-mapping',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. AI 파싱 및 검증 로그 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            log_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES disclosures(doc_id)
        )
    """)

    conn.commit()
    conn.close()


def save_disclosure_record(data: Dict[str, Any]) -> str:
    """공시 레코드를 DB에 저장하거나 업데이트합니다."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    doc_id = data.get("doc_id") or f"DISC-{data.get('date', '').replace('-', '')}-{os.urandom(2).hex().upper()}"
    filename = data.get("filename", "공시 문서")
    event = data.get("event", "주요사항보고서")
    title = data.get("title", "공시 보고서")
    reporter = data.get("reporter", "(주)와이바이오로직스")
    date_str = data.get("date", "")
    complete_date = data.get("complete_date", "")
    amount = str(data.get("amount", ""))
    counterparty = data.get("counterparty", "")
    asset_type = data.get("asset_type", "")
    ratio = data.get("ratio", "")
    purpose = data.get("purpose", "")
    status = data.get("status", "ai-mapping")

    cursor.execute("""
        INSERT INTO disclosures (
            id, doc_id, filename, event, title, reporter, date, 
            complete_date, amount, counterparty, asset_type, ratio, purpose, status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(doc_id) DO UPDATE SET
            filename=excluded.filename,
            event=excluded.event,
            title=excluded.title,
            reporter=excluded.reporter,
            date=excluded.date,
            complete_date=excluded.complete_date,
            amount=excluded.amount,
            counterparty=excluded.counterparty,
            asset_type=excluded.asset_type,
            ratio=excluded.ratio,
            purpose=excluded.purpose,
            status=excluded.status,
            updated_at=CURRENT_TIMESTAMP
    """, (doc_id, doc_id, filename, event, title, reporter, date_str, complete_date, amount, counterparty, asset_type, ratio, purpose, status))

    conn.commit()
    conn.close()
    return doc_id


def search_disclosures_db(query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    """DB에 저장된 공시 레코드를 키워드로 정밀 검색합니다."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    if query.strip():
        sql_query = """
            SELECT * FROM disclosures 
            WHERE title LIKE ? OR event LIKE ? OR counterparty LIKE ? OR filename LIKE ? OR doc_id LIKE ?
            ORDER BY updated_at DESC LIMIT ?
        """
        search_pattern = f"%{query.strip()}%"
        cursor.execute(sql_query, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, limit))
    else:
        cursor.execute("SELECT * FROM disclosures ORDER BY updated_at DESC LIMIT ?", (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
