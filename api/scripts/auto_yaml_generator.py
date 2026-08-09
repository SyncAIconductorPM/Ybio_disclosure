import argparse
import logging
import os
import re
import sys
import zipfile
from pathlib import Path

# 부모 디렉토리를 sys.path에 추가하여 api 모듈을 임포트 가능하도록 설정
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from api.services.gemini_service import _get_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
당신은 한국 공시 자동화(DART/KIND) 전문가입니다. 아래는 공시 서식 파일(.dsd) 내부의 XML 데이터입니다.
이 XML 안에는 ACODE, AUNIT, ENG 등의 속성을 가진 여러 입력 필드들이 정의되어 있습니다.

사용자가 이 공시를 작성할 때 시스템에 입력해야 하는 항목들의 '의미론적(Semantic)' 뼈대를 YAML 형식으로 만들어주세요.
규칙:
1. YAML의 키(Key)는 사람이 직관적으로 이해할 수 있는 영문(소문자_스네이크)으로 작성하세요.
2. 각 필드에는 AI가 이해할 수 있도록 주석(#)으로 한글 설명을 덧붙이세요.
3. 예시 데이터(가짜 데이터)를 채워 넣어주세요.
4. 마크다운 백틱(```) 없이 순수 YAML 텍스트만 출력하세요.

[DSD XML 내용 일부]
{xml_content}
"""

def generate_yaml(dsd_path: str) -> bool:
    logger.info(f"DSD 파일 분석 시작: {dsd_path}")
    
    if not os.path.exists(dsd_path):
        logger.error(f"파일이 존재하지 않습니다: {dsd_path}")
        return False

    # 1. DSD 압축 해제 및 XML 추출
    try:
        with zipfile.ZipFile(dsd_path, 'r') as z:
            # contents.xml을 우선적으로 찾음
            if 'contents.xml' in z.namelist():
                xml_data = z.read('contents.xml').decode('utf-8', errors='ignore')
            elif 'body.xml' in z.namelist():
                xml_data = z.read('body.xml').decode('utf-8', errors='ignore')
            else:
                xml_files = [f for f in z.namelist() if f.endswith('.xml')]
                if not xml_files:
                    logger.error("DSD 내부에 XML 파일이 존재하지 않습니다.")
                    return False
                xml_data = z.read(xml_files[0]).decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"DSD 파일 파싱 오류: {e}")
        return False

    # Gemini 컨텍스트 한도를 고려하여 텍스트 길이 조정
    xml_snippet = xml_data[:70000]

    logger.info("Gemini API로 YAML 스키마 생성 요청 중...")
    try:
        model = _get_client()
        prompt = PROMPT_TEMPLATE.format(xml_content=xml_snippet)
        response = model.generate_content(prompt)
        yaml_text = response.text.strip()
        
        # 마크다운 백틱 제거
        yaml_text = re.sub(r'^```(yaml)?\n?', '', yaml_text, flags=re.IGNORECASE)
        yaml_text = re.sub(r'\n?```$', '', yaml_text)
        
        # 저장 경로 생성
        base_name = Path(dsd_path).stem
        samples_dir = Path('samples')
        samples_dir.mkdir(exist_ok=True)
        save_path = samples_dir / f"{base_name}.yaml"
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(yaml_text)
            
        logger.info(f"성공적으로 YAML 파일이 생성되었습니다: {save_path}")
        return True
        
    except Exception as e:
        logger.error(f"YAML 스키마 생성 실패: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Semantic YAML from DSD template")
    parser.add_argument("dsd_path", help="Path to the target .dsd file")
    args = parser.parse_args()
    
    generate_yaml(args.dsd_path)
