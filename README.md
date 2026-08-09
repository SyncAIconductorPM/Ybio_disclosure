# 🚀 공시업무 자동화 시스템 (Disclosure AI)

YBioLogics의 공시 업무(DART, KIND)를 돕는 AI 기반 자동화 시스템입니다.
AI는 비정형 자료에서 공시 데이터를 추출하고 양식을 채워주며, **최종 검토 및 제출은 사용자가 공동인증서를 통해 직접 수행**하는 **Human-in-the-loop** 구조를 준수합니다.

---

## 📜 버전 히스토리 (Version History)

| 버전 | 출시일 | 주요 기능 및 변경 사항 |
| :--- | :--- | :--- |
| **v1.0.0** | 2026-08-09 | • **양식별 Pydantic 법규 검증 레이어 구축** (`api/forms/` 8종 서식 스키마)<br>• **DataSource Protocol 개발** (`data_source.py` 토큰 동적 치환)<br>• **Gemini Tool-Use 멀티턴 에이전트 서비스 통합** (`agent_service.py`) <br>• **Playwright 보안 팝업 자동 디스미스 및 UA 스푸핑 구현** (`browser_service.py`) <br>• **21개 전체 단위 및 통합 테스트 100% 통과 (PASSED)** |
| **v0.8.0** | 2026-08-09 | • 8종 가상 공시 테스트 데이터 구축 (`samples/*.yaml`, `mock_license_out_contract.txt` 등)<br>• 파일 업로드 시 업로드 문서 기반 동적 AI 인사이트 로그 및 DART/KIND 폼 맵핑 구현<br>• 토스트 알림창 자동 닫힘 제거 및 수동 `✕` 닫기 버튼 적용 |
| **v0.5.0** | 2026-08-09 | • DART .dsd XML 규격 검증 엔진 통합 (`api/services/dsd_service.py`) <br>• DART 셀 빈값(`-` 채움), 단위코드(`AUNITVALUE`), `TR` 행 수 보존 규칙 2차 검증 구현<br>• `@lru_cache` 템플릿 메모리 캐싱 및 `io.BytesIO` 바이너리 패키징 적용 |
| **v0.1.0** | 2026-08-08 | • 초기 MVP 개발 및 기본 REST API 라우터 구조 설계 |

---

## 🛠️ 빠른 시작 (Quick Start)

```bash
# 1. 의존성 확인 및 서버 실행
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 2. 브라우저 접속
# 메인 대시보드: http://localhost:8000/
# 워크스페이스: http://localhost:8000/workspace.html
# Swagger API 문서: http://localhost:8000/docs
```

## 🧪 테스트 실행 (Pytest)

```bash
# 21개 전체 단위 및 통합 테스트 실행
py -m pytest tests/ -v
```

자세한 제품 요구사항 및 사양은 [PRD.md](file:///c:/Make_project/disclosure/PRD.md)를 참고하세요.
