import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from api.config import get_settings
from api.scripts.auto_yaml_generator import generate_yaml
from api.services.dsd_service import (
    DartValidationError,
    build_dsd_in_memory,
    get_templates_root,
    list_templates,
    read_template,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates", tags=["Templates"])


class BuildDsdRequest(BaseModel):
    """.dsd 생성 요청 모델"""
    contents_xml: str
    meta_xml: str
    template_name: str | None = None
    strict_validation: bool = True


@router.get("", summary="전체 템플릿 목록 조회")
async def get_templates():
    """
    templates/dsd/empty/ 폴더 내에 존재하는 .dsd 파일들의 이름을 반환합니다.
    (확장자 제외)
    """
    try:
        dsd_dir = get_templates_root() / "empty"
        if not dsd_dir.exists():
            return {"templates": []}
            
        templates = [p.stem for p in dsd_dir.glob("*.dsd")]
        return {"templates": sorted(templates)}
    except Exception as exc:
        logger.error("템플릿 목록 조회 중 오류: %s", exc)
        raise HTTPException(status_code=500, detail=f"템플릿 목록을 조회할 수 없습니다: {exc}")


@router.get("/status", summary="템플릿 매핑 상태 조회")
async def get_templates_status():
    """
    모든 템플릿 목록과 YAML 변환 완료 여부를 반환합니다.
    """
    dsd_dir = Path("templates/dsd/empty")
    samples_dir = Path("samples")
    
    if not dsd_dir.exists():
        return {"items": []}
        
    results = []
    for dsd_path in dsd_dir.glob("*.dsd"):
        base_name = dsd_path.stem
        yaml_path = samples_dir / f"{base_name}.yaml"
        results.append({
            "name": base_name,
            "ready": yaml_path.exists()
        })
        
    # 이름순 정렬
    results.sort(key=lambda x: x["name"])
    return {"items": results}

@router.post("/convert/{template_name}", summary="단일 템플릿 변환")
async def convert_single_template(template_name: str):
    """
    특정 템플릿 1건에 대해서만 YAML 변환을 시도합니다.
    """
    dsd_path = Path("templates/dsd/empty") / f"{template_name}.dsd"
    yaml_path = Path("samples") / f"{template_name}.yaml"
    
    if not dsd_path.exists():
        raise HTTPException(status_code=404, detail="해당 템플릿(.dsd) 파일이 존재하지 않습니다.")
    
    if yaml_path.exists():
        return {"status": "success", "message": "이미 변환이 완료된 템플릿입니다."}
        
    logger.info(f"단일 템플릿 자동 변환 시작: {template_name}")
    success = generate_yaml(str(dsd_path))
    
    if success:
        return {"status": "success", "message": f"{template_name} 템플릿 변환 완료"}
    else:
        raise HTTPException(status_code=500, detail=f"{template_name} 변환 중 오류가 발생했습니다.")

@router.post("/sync", summary="템플릿 전체 자동 동기화")
async def sync_templates():
    """
    templates/dsd/empty/ 폴더를 스캔하여 새로운 .dsd 파일을 찾고,
    매칭되는 .yaml 파일이 없으면 자동으로 생성합니다.
    """
    dsd_dir = Path("templates/dsd/empty")
    samples_dir = Path("samples")
    
    if not dsd_dir.exists():
        raise HTTPException(status_code=404, detail="템플릿 폴더가 존재하지 않습니다.")
        
    samples_dir.mkdir(exist_ok=True)
    
    new_generated = []
    failed = []
    
    # .dsd 파일 스캔
    for dsd_path in dsd_dir.glob("*.dsd"):
        base_name = dsd_path.stem
        yaml_path = samples_dir / f"{base_name}.yaml"
        
        # 짝이 맞는 yaml 파일이 없으면 생성
        if not yaml_path.exists():
            logger.info(f"새로운 템플릿 발견: {base_name}.dsd")
            success = generate_yaml(str(dsd_path))
            if success:
                new_generated.append(base_name)
            else:
                failed.append(base_name)
                
    return {
        "status": "success",
        "generated_count": len(new_generated),
        "generated_files": new_generated,
        "failed_files": failed
    }


from fastapi import UploadFile, File

@router.post("/upload", summary="새 .dsd 템플릿 파일 업로드 및 AI 스키마 자동 변환")
async def upload_and_convert_template(file: UploadFile = File(...)):
    """
    사용자가 업로드한 .dsd 템플릿 파일(.dsd ZIP)을 받아 templates/dsd/empty/ 폴더에 보관하고,
    AI 스키마(YAML)를 즉시 자동 생성하여 변환합니다.
    """
    if not file.filename.endswith(".dsd"):
        raise HTTPException(status_code=400, detail="올바른 .dsd 템플릿 파일만 업로드할 수 있습니다.")

    try:
        dsd_dir = Path("templates/dsd/empty")
        dsd_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = dsd_dir / file.filename
        content = await file.read()
        
        with open(target_path, "wb") as f:
            f.write(content)

        base_name = target_path.stem
        logger.info("신규 .dsd 템플릿 파일 저장 완료: %s", target_path)

        # AI 스키마 (YAML) 즉시 변환 실행
        yaml_success = generate_yaml(str(target_path))

        return {
            "status": "success",
            "template_name": base_name,
            "filename": file.filename,
            "yaml_generated": yaml_success,
            "message": f"'{base_name}' 템플릿이 성공적으로 업로드되고 AI 스키마가 변환되었습니다."
        }
    except Exception as exc:
        logger.error("템플릿 업로드 및 변환 중 오류: %s", exc)
        raise HTTPException(status_code=500, detail=f"템플릿 업로드 처리 중 오류 발생: {exc}")


import yaml

@router.get("/schema/{template_name}", summary="템플릿의 YAML 스키마 및 폼 필드 메타데이터 조회")
async def get_template_schema(template_name: str):
    """
    템플릿명에 해당하는 YAML 스키마(samples/*.yaml)를 파싱하여, 
    프론트엔드가 폼 영역의 필드 라벨을 100% 자율 동적 생성할 수 있도록 구조 메타데이터를 반환합니다.
    """
    try:
        samples_dir = Path("samples")
        yaml_path = samples_dir / f"{template_name}.yaml"

        if not yaml_path.exists():
            # 부분 일치 검색
            candidates = list(samples_dir.glob("*.yaml"))
            for c in candidates:
                if template_name in c.stem or c.stem in template_name:
                    yaml_path = c
                    break

        if not yaml_path.exists():
            return {
                "status": "not_found",
                "template_name": template_name,
                "fields": []
            }

        with open(yaml_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        if not isinstance(raw_data, dict):
            return {"status": "success", "template_name": template_name, "fields": []}

        # YAML 데이터를 기반으로 프론트엔드 동적 라벨 메타데이터 변환
        fields_metadata = []
        for key, val in raw_data.items():
            if key in ["event", "reporter"]:
                continue
            fields_metadata.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "value": str(val) if val is not None else ""
            })

        return {
            "status": "success",
            "template_name": template_name,
            "raw_yaml": raw_data,
            "fields": fields_metadata
        }
    except Exception as exc:
        logger.error("YAML 스키마 조회 중 오류: %s", exc)
        raise HTTPException(status_code=500, detail=f"스키마 조회 오류: {exc}")




@router.post("/build", summary=".dsd 바이너리 빌드 및 다운로드")
async def build_dsd_file(body: BuildDsdRequest):
    """
    제공된 contents.xml 및 meta.xml을 검증하고 .dsd ZIP 바이너리를 생성하여 직접 반환합니다.
    """
    try:
        empty_xml = None
        if body.template_name:
            empty_path = get_templates_root() / "empty" / f"{body.template_name}.dsd"
            if empty_path.is_file():
                empty_tpl = read_template(empty_path)
                empty_xml = empty_tpl["contents_xml"]

        dsd_bytes = build_dsd_in_memory(
            contents_xml=body.contents_xml,
            meta_xml=body.meta_xml,
            empty_xml=empty_xml,
            strict_validation=body.strict_validation,
        )

        filename = f"{body.template_name or 'filled_document'}.dsd"
        headers = {
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
        return Response(content=dsd_bytes, media_type="application/octet-stream", headers=headers)

    except DartValidationError as exc:
        raise HTTPException(status_code=400, detail={"errors": exc.errors, "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(".dsd 바이너리 빌드 실패: %s", exc)
        raise HTTPException(status_code=500, detail=f".dsd 빌드 중 오류가 발생했습니다: {exc}")

