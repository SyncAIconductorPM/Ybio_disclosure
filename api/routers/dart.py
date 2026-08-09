"""
api/routers/dart.py – OpenDART API 라우터
GET /dart/company        기업 기본 정보 조회
GET /dart/disclosures    공시 목록 조회
GET /dart/search         회사명 검색
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.services import dart_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dart", tags=["OpenDART"])


# ── 응답 스키마 ──────────────────────────────────────────────────────────


class CompanyInfo(BaseModel):
    """기업 기본 정보"""
    corp_code: str | None = None
    corp_name: str | None = None
    corp_name_eng: str | None = None
    stock_name: str | None = None
    stock_code: str | None = None
    ceo_nm: str | None = None
    corp_cls: str | None = None   # Y:유가, K:코스닥, N:코넥스, E:기타
    jurir_no: str | None = None
    bizr_no: str | None = None
    adres: str | None = None
    hm_url: str | None = None
    ir_url: str | None = None
    phn_no: str | None = None
    fax_no: str | None = None
    ind_tp: str | None = None


class DisclosureItem(BaseModel):
    """공시 목록 개별 항목"""
    rcept_no: str | None = None
    corp_cls: str | None = None
    corp_code: str | None = None
    corp_name: str | None = None
    report_nm: str | None = None
    rcept_dt: str | None = None
    flr_nm: str | None = None
    rm: str | None = None


class DisclosureListResponse(BaseModel):
    """공시 목록 응답"""
    total_count: int
    list: list[DisclosureItem]


# ── 엔드포인트 ──────────────────────────────────────────────────────────


@router.get(
    "/company",
    response_model=CompanyInfo,
    summary="기업 기본 정보 조회",
    description="OpenDART 기업 고유번호(corp_code)로 기업 정보를 조회합니다.",
)
async def get_company(
    corp_code: str = Query(
        ...,
        description="OpenDART 기업 고유번호 (8자리 숫자)",
        min_length=1,
        max_length=8,
        pattern=r"^\d+$",
        example="00126380",
    ),
) -> CompanyInfo:
    """
    OpenDART에서 기업 기본 정보를 조회합니다.

    에러 케이스:
    - 400: 잘못된 corp_code 형식
    - 404: 해당 기업 없음
    - 503: OpenDART API 연결 실패
    """
    try:
        data = await dart_service.get_company_info(corp_code)
        return CompanyInfo(**{k: v for k, v in data.items() if k in CompanyInfo.model_fields})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get(
    "/disclosures",
    response_model=DisclosureListResponse,
    summary="공시 목록 조회",
    description="특정 기업의 공시 목록을 날짜 범위로 조회합니다.",
)
async def get_disclosures(
    corp_code: str = Query(
        ...,
        description="OpenDART 기업 고유번호",
        pattern=r"^\d+$",
        example="00126380",
    ),
    bgn_de: str | None = Query(
        default=None,
        description="시작일 (YYYYMMDD)",
        pattern=r"^\d{8}$",
        example="20240101",
    ),
    end_de: str | None = Query(
        default=None,
        description="종료일 (YYYYMMDD)",
        pattern=r"^\d{8}$",
        example="20241231",
    ),
    page_no: int = Query(default=1, ge=1, description="페이지 번호"),
    page_count: int = Query(default=20, ge=1, le=100, description="페이지당 건수"),
) -> DisclosureListResponse:
    """
    OpenDART에서 기업 공시 목록을 조회합니다.

    에러 케이스:
    - 400: 잘못된 파라미터
    - 503: OpenDART API 연결 실패
    """
    try:
        result = await dart_service.get_disclosures(
            corp_code=corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
            page_no=page_no,
            page_count=page_count,
        )
        items = [
            DisclosureItem(**{k: v for k, v in item.items() if k in DisclosureItem.model_fields})
            for item in result.get("list", [])
        ]
        return DisclosureListResponse(
            total_count=result["total_count"],
            list=items,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/search",
    summary="회사명으로 기업 검색",
    description="회사명으로 OpenDART 기업 고유번호를 검색합니다.",
)
async def search_company(
    q: str = Query(
        ...,
        description="검색할 회사명 (부분 일치)",
        min_length=2,
        example="에이비오",
    ),
) -> list[dict]:
    """
    회사명으로 기업 정보를 검색합니다.

    에러 케이스:
    - 400: 검색어 너무 짧음
    - 503: OpenDART API 연결 실패
    """
    try:
        results = await dart_service.search_corp_code(q)
        return results
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
