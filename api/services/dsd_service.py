"""
api/services/dsd_service.py – DART .dsd 템플릿 파싱, DART XML 규격 검증 및 패키징 서비스

DART/KIND 전자공시 서식(.dsd, ZIP 압축 내 contents.xml 및 meta.xml)을 다루며,
DART 편집기가 요구하는 엄격한 XML 스키마 규격(빈 셀 처리, AUNIT/AUNITVALUE, TR 행 수 보존 등)을
사전에 검증하고 패키징하는 통합 서비스 모듈입니다.
"""

import io
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.config import get_settings

logger = logging.getLogger(__name__)

# DART .dsd 파일 내부 표준 파일명
CONTENTS_FILE = "contents.xml"
META_FILE = "meta.xml"

# 정규식 패턴
_SAFE_FILENAME_PATTERN = re.compile(r"[^\w.\- ()가-힣]+")
_DOC_NAME_PATTERN = re.compile(r"<DOCUMENT-NAME[^>]*>([^<]+)</DOCUMENT-NAME>")

# 템플릿 종류 매핑
_FOLDER_TO_KIND = {"empty": "empty", "examples": "example"}


class DartValidationError(ValueError):
    """DART 편집기 스키마 유효성 검사 실패 시 발생하는 예외 클래스."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("DART 편집기 규격 오류:\n" + "\n".join(f"- {e}" for e in errors))


@dataclass
class DsdTemplateInfo:
    """DSD 템플릿 메타 정보 데이터 클래스."""

    kind: str  # "empty" | "example"
    name: str  # 템플릿 파일명 (예: 사업보고서.dsd)
    path: Path  # 파일 절대 경로


def get_templates_root() -> Path:
    """설정에서 지정된 템플릿 디렉토리 경로를 반환합니다."""
    settings = get_settings()
    return settings.templates_dir


def list_templates() -> list[DsdTemplateInfo]:
    """
    사용 가능한 .dsd 템플릿 목록을 조회합니다.

    Returns:
        DsdTemplateInfo 객체 리스트

    Raises:
        RuntimeError: 템플릿 디렉토리 접근 오류 시
    """
    root = get_templates_root()
    result: list[DsdTemplateInfo] = []

    try:
        for folder_name, kind in _FOLDER_TO_KIND.items():
            folder = root / folder_name
            if not folder.is_dir():
                continue
            for p in sorted(folder.glob("*.dsd")):
                result.append(DsdTemplateInfo(kind=kind, name=p.name, path=p))
        logger.info("템플릿 목록 조회 성공: %d개 발견", len(result))
        return result
    except Exception as exc:
        logger.error("템플릿 목록 조회 실패 (경로: %s): %s", root, exc)
        raise RuntimeError(f"템플릿 목록을 조회할 수 없습니다: {exc}") from exc


def read_template(path: Path) -> dict[str, str]:
    """
    .dsd ZIP 파일에서 contents.xml 및 meta.xml 텍스트를 파싱하여 반환합니다.

    Args:
        path: .dsd 파일 경로

    Returns:
        {"contents_xml": str, "meta_xml": str}

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 경우
        ValueError: ZIP 압축 해제 실패 또는 XML 문법 오류 시
    """
    if not path.exists():
        raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: '{path}'")

    try:
        with zipfile.ZipFile(path, "r") as z:
            names = set(z.namelist())
            if CONTENTS_FILE not in names or META_FILE not in names:
                raise ValueError(f"'{path.name}' 파일에 {CONTENTS_FILE} 또는 {META_FILE}이 누락되었습니다.")

            contents_xml = z.read(CONTENTS_FILE).decode("utf-8")
            meta_xml = z.read(META_FILE).decode("utf-8")

        _validate_xml_syntax(f"{path.name}:{CONTENTS_FILE}", contents_xml)
        _validate_xml_syntax(f"{path.name}:{META_FILE}", meta_xml)

        return {"contents_xml": contents_xml, "meta_xml": meta_xml}

    except zipfile.BadZipFile as exc:
        logger.error("손상된 .dsd ZIP 파일: %s - %s", path, exc)
        raise ValueError(f"'{path.name}'은(는) 올바른 .dsd ZIP 파일이 아닙니다.") from exc
    except Exception as exc:
        logger.error(".dsd 템플릿 읽기 오류 (%s): %s", path, exc)
        raise


@lru_cache(maxsize=32)
def _read_cached_empty_template(path: Path) -> dict[str, str]:
    """empty 템플릿 XML 읽기 결과를 메모리에 캐싱하여 성능을 최적화합니다."""
    return read_template(path)


def _validate_xml_syntax(label: str, text: str) -> None:
    """XML 구문 유효성을 검사합니다."""
    try:
        ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"'{label}' XML 구문 오류: {exc}") from exc


def extract_document_name(contents_xml: str) -> str | None:
    """contents.xml 문서 내부의 <DOCUMENT-NAME> 태그 값을 추출합니다."""
    match = _DOC_NAME_PATTERN.search(contents_xml)
    return match.group(1).strip() if match else None


def find_empty_template_by_name(doc_name: str) -> Path | None:
    """
    문서명에 일치하는 empty 템플릿(.dsd) 파일 경로를 찾습니다.

    Args:
        doc_name: 공시 문서명 (예: "사업보고서")

    Returns:
        템플릿 Path 또는 None
    """
    root = get_templates_root()
    # 접미사 .dsd 자동 처리
    file_name = doc_name if doc_name.endswith(".dsd") else f"{doc_name}.dsd"
    candidate = root / "empty" / file_name

    if candidate.is_file():
        return candidate

    # 부분 일치 검색
    try:
        empty_dir = root / "empty"
        if empty_dir.is_dir():
            for p in empty_dir.glob("*.dsd"):
                if doc_name in p.stem or p.stem in doc_name:
                    return p
    except Exception as exc:
        logger.warning("템플릿 일치 검색 중 오류 (doc_name=%s): %s", doc_name, exc)

    return None


def validate_against_template(contents_xml: str, empty_xml: str) -> list[str]:
    """
    DART 편집기 사전 검증 로직:
    1. <TE>/<TU> 데이터 셀 필수값 검증 (빈 셀은 '-' 입력 필수)
    2. <TU AUNIT="..."> 태그는 AUNITVALUE (단위) 선택 필수
    3. TABLE-GROUP 및 TBODY 내 <TR> 행 수 보존 검증 (템플릿 대비 행 삭제 방지)

    Args:
        contents_xml: 검증할 생성/채워진 XML 문자열
        empty_xml: 비교 대상이 되는 빈 템플릿 XML 문자열

    Returns:
        오류 메시지 문자열 리스트 (오류가 없으면 빈 리스트)
    """
    errors: list[str] = []

    try:
        root = ET.fromstring(contents_xml)
        empty_root = ET.fromstring(empty_xml)
    except ET.ParseError as exc:
        return [f"XML 구문 해석 오류: {exc}"]

    # 1. 셀 누락 및 단위 코드 검증
    for elem in root.iter():
        if elem.tag not in ("TE", "TU"):
            continue
        # 업데이트 불가 셀 무시
        if elem.get("AUPDATECONT") == "N":
            continue

        text = "".join(elem.itertext()).strip()
        if not text:
            attr = "ACODE" if elem.get("ACODE") else "AUNIT"
            code = elem.get(attr) or "?"
            errors.append(
                f"빈 셀 누락 <{elem.tag} {attr}=\"{code}\">: DART 규격상 데이터 또는 '-'를 입력해야 합니다."
            )

        if elem.tag == "TU" and elem.get("AUNIT") and not (elem.get("AUNITVALUE") or "").strip():
            errors.append(
                f"<TU AUNIT=\"{elem.get('AUNIT')}\">: 단위(AUNITVALUE) 선택이 누락되었습니다."
            )

    # 2. TABLE-GROUP 및 TR 행 개수 검증
    e_tgs = list(empty_root.iter("TABLE-GROUP"))
    g_tgs = list(root.iter("TABLE-GROUP"))

    if len(e_tgs) != len(g_tgs):
        errors.append(
            f"TABLE-GROUP 구조 불일치: 템플릿({len(e_tgs)}개) vs 생성본({len(g_tgs)}개). TABLE-GROUP을 추가하거나 삭제할 수 없습니다."
        )

    for e_tg, g_tg in zip(e_tgs, g_tgs):
        cls = e_tg.get("ACLASS", "?")
        e_tbs = list(e_tg.iter("TBODY"))
        g_tbs = list(g_tg.iter("TBODY"))

        for e_tb, g_tb in zip(e_tbs, g_tbs):
            e_rows = len(e_tb.findall("TR"))
            g_rows = len(g_tb.findall("TR"))
            if g_rows < e_rows:
                errors.append(
                    f"표(ACLASS=\"{cls}\") 행 삭제 오류: 템플릿({e_rows}행) 대비 생성본({g_rows}행)에 누락이 발생했습니다. "
                    "삭제된 행을 복구하고 빈 셀은 '-'로 채워야 합니다."
                )

    return errors


def sanitize_filename(name: str) -> str:
    """안전한 파일명 문자열로 정화합니다."""
    clean = name.strip().rstrip(".")
    clean = _SAFE_FILENAME_PATTERN.sub("_", clean) or "disclosure_doc"
    if not clean.endswith(".dsd"):
        clean = f"{clean}.dsd"
    return clean


def build_dsd_in_memory(
    contents_xml: str,
    meta_xml: str,
    empty_xml: str | None = None,
    strict_validation: bool = True,
) -> bytes:
    """
    메모리 상에서 DART .dsd (ZIP) 바이너리를 생성합니다.

    Args:
        contents_xml: 완성된 contents.xml 문자열
        meta_xml: 메타 meta.xml 문자열
        empty_xml: (선택) 검증용 empty 템플릿 XML 문자열
        strict_validation: True일 경우 DART 검증 실패 시 DartValidationError 발생

    Returns:
        .dsd 파일 바이너리 (bytes)

    Raises:
        DartValidationError: 규격 검증 실패 시
        ValueError: XML 문법 오류 시
    """
    _validate_xml_syntax("contents_xml", contents_xml)
    _validate_xml_syntax("meta_xml", meta_xml)

    if strict_validation and empty_xml:
        errors = validate_against_template(contents_xml, empty_xml)
        if errors:
            raise DartValidationError(errors)

    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(CONTENTS_FILE, contents_xml.encode("utf-8"))
            z.writestr(META_FILE, meta_xml.encode("utf-8"))
        return buf.getvalue()
    except Exception as exc:
        logger.error("메모리 .dsd 생성 중 압축 오류: %s", exc)
        raise RuntimeError(f".dsd 바이너리 패키징 실패: {exc}") from exc


def write_filled_dsd(
    contents_xml: str,
    meta_xml: str,
    output_name: str | None = None,
    strict_validation: bool = True,
) -> Path:
    """
    생성된 contents_xml 및 meta_xml을 검증하고 설정된 output_dir에 .dsd 파일로 저장합니다.

    Args:
        contents_xml: 본문 XML
        meta_xml: 메타 XML
        output_name: 저장할 출력 파일명 (기본값: filled_YYYYMMDD_HHMMSS.dsd)
        strict_validation: 엄격한 규격 검증 여부

    Returns:
        저장된 파일의 절대 경로 (Path)
    """
    settings = get_settings()
    output_dir = settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # empty 템플릿 검색 및 2차 검증
    doc_name = extract_document_name(contents_xml)
    empty_xml = None
    if doc_name:
        empty_path = find_empty_template_by_name(doc_name)
        if empty_path:
            try:
                empty_data = _read_cached_empty_template(empty_path)
                empty_xml = empty_data["contents_xml"]
            except Exception as exc:
                logger.warning("empty 템플릿 캐싱 읽기 실패 (%s): %s", empty_path, exc)

    dsd_bytes = build_dsd_in_memory(
        contents_xml=contents_xml,
        meta_xml=meta_xml,
        empty_xml=empty_xml,
        strict_validation=strict_validation,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = sanitize_filename(output_name or f"filled_{stamp}.dsd")
    final_file = output_dir / f"{stamp}_{base_name}"

    try:
        final_file.write_bytes(dsd_bytes)
        logger.info(".dsd 파일 생성 완: %s (%d bytes)", final_file, len(dsd_bytes))
        return final_file
    except Exception as exc:
        logger.error(".dsd 디스크 저장 오류 (%s): %s", final_file, exc)
        raise RuntimeError(f"파일 저장 중 오류가 발생했습니다: {exc}") from exc
