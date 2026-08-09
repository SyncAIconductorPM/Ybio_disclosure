"""
api/services/dart_service.py – OpenDART REST API 래퍼
금융감독원 OpenDART API를 통해 회사정보 및 공시 목록을 조회합니다.

API 문서: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001
규칙: 에러 처리 포함, API 키 하드코딩 금지
"""

import logging
from typing import Any

import httpx

from api.config import get_settings

logger = logging.getLogger(__name__)

# OpenDART API 요청 타임아웃 (초)
_REQUEST_TIMEOUT = 15.0


def _make_client() -> httpx.AsyncClient:
    """공통 헤더를 포함한 httpx 비동기 클라이언트를 생성합니다."""
    return httpx.AsyncClient(
        timeout=_REQUEST_TIMEOUT,
        headers={"Accept": "application/json"},
    )


async def get_company_info(corp_code: str) -> dict[str, Any]:
    """
    OpenDART에서 기업 기본 정보를 조회합니다.

    Args:
        corp_code: OpenDART 기업 고유번호 (8자리 숫자 문자열)

    Returns:
        기업 정보 딕셔너리 (corp_name, ceo_nm, adres, stock_code 등)

    Raises:
        ValueError: 잘못된 corp_code 또는 API 오류 상태
        RuntimeError: 네트워크 오류 시
    """
    settings = get_settings()

    if not corp_code or not corp_code.isdigit():
        raise ValueError(f"corp_code는 숫자 문자열이어야 합니다: '{corp_code}'")

    url = f"{settings.opendart_base_url}/company.json"
    params = {
        "crtfc_key": settings.opendart_api_key,
        "corp_code": corp_code,
    }

    try:
        async with _make_client() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status", "")
        if status != "000":
            msg = data.get("message", "알 수 없는 오류")
            logger.error("OpenDART company API 오류 [%s]: %s", status, msg)
            raise ValueError(f"OpenDART 오류 ({status}): {msg}")

        logger.info("OpenDART 기업 정보 조회 성공: %s", data.get("corp_name"))
        return data

    except httpx.HTTPStatusError as exc:
        logger.error("OpenDART HTTP 오류: %s", exc)
        raise RuntimeError(f"OpenDART HTTP 오류: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.error("OpenDART 네트워크 오류: %s", exc)
        raise RuntimeError("OpenDART 서버에 연결할 수 없습니다.") from exc


async def get_disclosures(
    corp_code: str,
    bgn_de: str | None = None,
    end_de: str | None = None,
    page_no: int = 1,
    page_count: int = 20,
) -> dict[str, Any]:
    """
    OpenDART에서 기업 공시 목록을 조회합니다.

    Args:
        corp_code: OpenDART 기업 고유번호
        bgn_de: 시작일 (YYYYMMDD)
        end_de: 종료일 (YYYYMMDD)
        page_no: 페이지 번호 (1부터 시작)
        page_count: 페이지당 건수 (최대 100)

    Returns:
        { "total_count": int, "list": [ {...} ] }

    Raises:
        ValueError: API 오류 상태
        RuntimeError: 네트워크 오류
    """
    settings = get_settings()

    url = f"{settings.opendart_base_url}/list.json"
    params: dict[str, Any] = {
        "crtfc_key": settings.opendart_api_key,
        "corp_code": corp_code,
        "page_no": page_no,
        "page_count": min(page_count, 100),
    }
    if bgn_de:
        params["bgn_de"] = bgn_de
    if end_de:
        params["end_de"] = end_de

    try:
        async with _make_client() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status", "")
        if status not in ("000",):
            # 013 = 조회 결과 없음 (에러가 아님)
            if status == "013":
                logger.info("OpenDART 공시 조회 결과 없음 (corp_code=%s)", corp_code)
                return {"total_count": 0, "list": []}
            msg = data.get("message", "알 수 없는 오류")
            logger.error("OpenDART list API 오류 [%s]: %s", status, msg)
            raise ValueError(f"OpenDART 오류 ({status}): {msg}")

        result = {
            "total_count": int(data.get("total_count", 0)),
            "list": data.get("list", []),
        }
        logger.info(
            "OpenDART 공시 목록 조회 성공: %d건 (corp_code=%s)",
            result["total_count"],
            corp_code,
        )
        return result

    except httpx.HTTPStatusError as exc:
        logger.error("OpenDART HTTP 오류: %s", exc)
        raise RuntimeError(f"OpenDART HTTP 오류: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.error("OpenDART 네트워크 오류: %s", exc)
        raise RuntimeError("OpenDART 서버에 연결할 수 없습니다.") from exc


async def search_corp_code(company_name: str) -> list[dict[str, Any]]:
    """
    회사명으로 OpenDART 기업 고유번호를 검색합니다.

    Args:
        company_name: 검색할 회사명 (부분 일치)

    Returns:
        매칭된 기업 목록 [ {corp_code, corp_name, stock_code, ...} ]
    """
    settings = get_settings()

    url = f"{settings.opendart_base_url}/corpCode.xml"
    # OpenDART는 전체 corp_code 목록을 ZIP으로만 제공하므로
    # 검색은 /company.json 에 corp_name 파라미터로 수행
    params = {
        "crtfc_key": settings.opendart_api_key,
        "corp_name": company_name,
        "page_no": 1,
        "page_count": 10,
    }

    # 사실 list.json은 corp_code 필수이므로 검색용 별도 엔드포인트 사용
    search_url = f"{settings.opendart_base_url}/company.json"
    search_params = {
        "crtfc_key": settings.opendart_api_key,
        "corp_name": company_name,
    }

    try:
        async with _make_client() as client:
            resp = await client.get(search_url, params=search_params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "000":
            # 단일 결과를 리스트로 래핑
            return [data]
        return []

    except Exception as exc:
        logger.error("OpenDART 회사 검색 오류: %s", exc)
        return []
