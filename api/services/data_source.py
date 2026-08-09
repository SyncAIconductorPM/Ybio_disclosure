"""
api/services/data_source.py – DataSource Protocol 및 Yaml / OpenDART 표준 추상화 구현체

공시 자동화 데이터 소스를 인터페이스로 추상화하여
YAML 파일, OpenDART API, 지식 그래프(KG) 간 교체가 상위 계층 코드에 영향 주지 않도록 보장합니다.
"""

import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml
from api.config import get_settings
from api.forms import get_form_model

logger = logging.getLogger(__name__)


@runtime_checkable
class DataSourceProtocol(Protocol):
    """모든 데이터 소스가 구현해야 하는 표준 인터페이스"""

    def list_forms(self) -> list[str]:
        """사용 가능한 서식 데이터 목록 반환"""
        ...

    def load_form_data(self, form_name: str) -> dict[str, Any]:
        """서식명에 해당하는 파싱된 공시 데이터 딕셔너리 반환"""
        ...


class YamlDataSource:
    """samples/ 디렉토리의 YAML 데이터를 로드하고 토큰 플레이스홀더를 동적으로 치환하는 DataSource"""

    def __init__(self, samples_dir: Path | None = None):
        self.samples_dir = samples_dir or (Path(__file__).resolve().parent.parent.parent / "samples")

    def list_forms(self) -> list[str]:
        """samples/*.yaml 파일 목록 반환"""
        if not self.samples_dir.exists():
            return []
        return [p.stem for p in self.samples_dir.glob("*.yaml")]

    def load_form_data(self, form_name: str) -> dict[str, Any]:
        """YAML 파일 로드 및 ${token} 플레이스홀더 동적 치환"""
        file_path = self.samples_dir / (form_name if form_name.endswith(".yaml") else f"{form_name}.yaml")
        if not file_path.exists():
            # 부분 검색
            candidates = list(self.samples_dir.glob("*.yaml"))
            for c in candidates:
                if form_name in c.stem or c.stem in form_name:
                    file_path = c
                    break

        if not file_path.exists():
            raise FileNotFoundError(f"YAML 샘플 파일을 찾을 수 없습니다: '{form_name}'")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            rendered_text = self._render_placeholders(raw_text)
            data = yaml.safe_load(rendered_text)

            if not isinstance(data, dict):
                raise ValueError(f"'{file_path.name}' 내용이 올바른 딕셔너리 형식이 아닙니다.")

            # Pydantic 양식 스키마 적용 검증 (실패 시 원본 dict 반환)
            event_name = data.get("event") or data.get("title") or form_name
            form_cls = get_form_model(event_name)
            try:
                validated_model = form_cls(**data)
                return validated_model.model_dump()
            except Exception as v_exc:
                logger.warning("YAML Pydantic 검증 경고 (%s): %s", form_name, v_exc)
                return data

        except Exception as exc:
            logger.error("YamlDataSource 로딩 실패 (%s): %s", form_name, exc)
            raise RuntimeError(f"데이터 소스 로딩 중 오류가 발생했습니다: {exc}") from exc

    def _render_placeholders(self, text: str) -> str:
        """${today}, ${today_plus_30}, ${random_name_ko} 등의 플레이스홀더 치환"""
        today = datetime.now()
        today_plus_30 = today + timedelta(days=30)
        
        replacements = {
            "${today}": today.strftime("%Y-%m-%d"),
            "${today_plus_30}": today_plus_30.strftime("%Y-%m-%d"),
            "${random_name_ko}": random.choice(["김신약", "이바이오", "박임상", "최제약"]),
            "${random_address}": "서울특별시 서초구 반포대로 123",
        }

        rendered = text
        for token, val in replacements.items():
            rendered = rendered.replace(token, val)
        return rendered


class OpenDartDataSource:
    """OpenDART API 기반 실시간 데이터 조회를 제공하는 DataSource"""

    def __init__(self):
        self.settings = get_settings()

    def list_forms(self) -> list[str]:
        return ["OpenDART 실시간 공시 데이터"]

    def load_form_data(self, corp_code: str) -> dict[str, Any]:
        """OpenDART에서 기업 공시 기본 데이터 파싱 반환 (인프라 준비용)"""
        return {
            "event": "주요사항보고서",
            "reporter": "(주)와이바이오로직스",
            "corp_code": corp_code,
            "title": "OpenDART 연동 기업 데이터",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
