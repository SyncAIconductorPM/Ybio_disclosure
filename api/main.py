"""
api/main.py – FastAPI 애플리케이션 진입점
공시업무 자동화 시스템 백엔드 서버

실행 방법:
  uvicorn api.main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import get_settings
from api.routers import dart, kind, upload, validate, templates, system

# ── 로깅 설정 ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── 앱 수명주기 ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 실행되는 수명주기 핸들러."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("공시업무 자동화 시스템 API 서버 시작")
    logger.info("Gemini 모델: %s", settings.gemini_model)
    logger.info("OpenDART 베이스 URL: %s", settings.opendart_base_url)
    logger.info("KIND 포털 URL: %s", settings.krx_url)
    logger.info("=" * 60)
    yield
    logger.info("API 서버 종료")


# ── FastAPI 앱 인스턴스 ────────────────────────────────────────────────────
app = FastAPI(
    title="공시업무 자동화 시스템 API",
    description=(
        "Human-in-the-loop 공시 자동화 백엔드.\n\n"
        "- **Gemini AI**: 문서 파싱 및 공시 필드 자동 추출\n"
        "- **OpenDART**: 기업 정보 및 공시 목록 조회\n"
        "- **KIND 자동화**: Playwright 기반 양식 자동 입력\n\n"
        "⚠️ 최종 제출은 반드시 담당자가 직접 수행합니다 (Human-in-the-loop)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS 미들웨어 ──────────────────────────────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 전역 예외 핸들러 ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """처리되지 않은 예외를 500 응답으로 변환합니다."""
    logger.error("처리되지 않은 예외 [%s %s]: %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"내부 서버 오류: {type(exc).__name__}"},
    )


from fastapi.staticfiles import StaticFiles
from pathlib import Path

# ── 정적 파일 & 프론트엔드 마운트 ─────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent
app.mount("/css", StaticFiles(directory=project_root / "css"), name="css")
app.mount("/js", StaticFiles(directory=project_root / "js"), name="js")

app.include_router(upload.router)
app.include_router(validate.router)
app.include_router(dart.router)
app.include_router(kind.router)
app.include_router(templates.router)
app.include_router(system.router)


@app.get("/", tags=["프론트엔드"], summary="메인 화면 (index.html)")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(project_root / "index.html")

@app.get("/{page_name}.html", tags=["프론트엔드"], summary="HTML 페이지 서비스")
async def read_html_page(page_name: str):
    from fastapi.responses import FileResponse
    file_path = project_root / f"{page_name}.html"
    if file_path.exists():
        return FileResponse(file_path)
    return FileResponse(project_root / "index.html")



from api.db import init_db, save_disclosure_record, search_disclosures_db

# ── 헬스체크 및 DB 엔드포인트 ──────────────────────────────────────────
@app.get("/health", tags=["시스템"], summary="헬스체크")
async def health_check() -> dict:
    """서버 상태 및 설정 정보를 반환합니다."""
    cfg = get_settings()
    init_db()
    return {
        "status": "ok",
        "gemini_model": cfg.gemini_model,
        "opendart_base_url": cfg.opendart_base_url,
        "kind_url": cfg.krx_url,
        "db": "initialized",
    }


@app.get("/api/disclosures/search", tags=["공시 DB"], summary="공시 이력 정밀 DB 검색")
async def search_disclosures_endpoint(q: str = "", limit: int = 50):
    """실무자용 DB 키워드 정밀 검색 API"""
    try:
        results = search_disclosures_db(query=q, limit=limit)
        return {"status": "success", "count": len(results), "query": q, "disclosures": results}
    except Exception as exc:
        logger.error("DB 검색 중 오류: %s", exc)
        return {"status": "error", "message": str(exc), "disclosures": []}


@app.post("/api/disclosures/save", tags=["공시 DB"], summary="공시 작성 데이터 DB 저장")
async def save_disclosure_endpoint(request: Request):
    """공시 파싱 초안 또는 수정한 데이터를 DB에 영구 기록합니다."""
    try:
        data = await request.json()
        doc_id = save_disclosure_record(data)
        return {"status": "success", "doc_id": doc_id, "message": "DB 저장 완료"}
    except Exception as exc:
        logger.error("DB 저장 중 오류: %s", exc)
        return {"status": "error", "message": str(exc)}



# ── 직접 실행 지원 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    cfg = get_settings()
    uvicorn.run(
        "api.main:app",
        host=cfg.api_host,
        port=cfg.api_port,
        reload=True,
        log_level="info",
    )
