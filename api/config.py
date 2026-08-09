"""
api/config.py – 환경 변수 설정 로더
.env 파일에서 API 키 및 설정 값을 로드합니다.

pydantic-settings를 사용해 타입 안전성과 유효성 검증을 보장합니다.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정 (환경 변수 / .env 기반)"""

    model_config = SettingsConfigDict(
        # 프로젝트 루트의 .env 파일을 읽음
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 정의되지 않은 변수는 무시
    )

    # ── Google Gemini AI ──────────────────────────────────────────────
    google_api_key: str
    # .env에 없거나 지원되지 않는 모델명이면 안정적인 기본값 사용
    gemini_model: str = "gemini-1.5-pro"

    # ── OpenDART ────────────────────────────────────────────────────────
    opendart_api_key: str
    opendart_base_url: str = "https://opendart.fss.or.kr/api"

    # ── KRX KIND 포털 ──────────────────────────────────────────────────
    krx_url: str = "https://filing.krx.co.kr/"
    krx_id: str
    krx_pw: str

    # ── 서버 설정 ──────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # 개발 환경에서는 모든 origin 허용, 운영은 실제 도메인으로 교체
    cors_origins: list[str] = ["*"]

    # ── 파일 업로드 제한 ───────────────────────────────────────────────
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
    ]

    # ── 디렉토리 경로 설정 ─────────────────────────────────────────────
    templates_dir: Path = Path(__file__).resolve().parent.parent / "templates" / "dsd"
    output_dir: Path = Path(__file__).resolve().parent.parent / "output"




@lru_cache
def get_settings() -> Settings:
    """싱글턴 Settings 인스턴스를 반환 (캐시됨)."""
    return Settings()
