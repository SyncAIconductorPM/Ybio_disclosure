# 📋 공시업무 자동화 시스템 (Disclosure AI) – 최종 제품 요구사항 정의서 (PRD)

> **프로젝트명:** YBioLogics 공시업무 자동화 시스템 (Human-in-the-loop Disclosure Automation)  
> **현재 버전:** `v1.0.0 (Full Compliance & Automation Release)`  
> **최종 수정일:** 2026년 08월 09일  
> **기술 스택:** Python 3.14 · FastAPI · Google Gemini · Playwright · PyYAML · Pydantic V2 · HTML5/CSS3/Vanilla JS

---

## 📜 1. 버전 히스토리 (Version History)

| 버전 | 변경 일자 | 변경 구분 | 주요 변경 및 리뉴얼 내용 | 작성자 / 담당자 |
| :--- | :--- | :--- | :--- | :--- |
| **v0.1.0** | 2026-08-08 | Initial MVP | • 초기 MVP 개발 및 기본 REST API 라우터 구조 설계<br>• Docker + Xvfb + noVNC 가상 디스플레이 렌더링 포트 구축<br>• 단발성 비정형 문서 파싱 및 기초 YAML 데이터 매핑 | 공시 개발팀 (전임자) |
| **v0.5.0** | 2026-08-09 | Feature | • DART .dsd XML 규격 검증 엔진 통합 (`api/services/dsd_service.py`) <br>• DART 셀 빈값(`-` 채움), 단위코드(`AUNITVALUE`), `TR` 행 수 보존 규칙 2차 검증 구현<br>• `@lru_cache` 템플릿 메모리 캐싱 및 `io.BytesIO` 바이너리 패키징으로 속도 최적화 | 공시 개발팀 |
| **v0.8.0** | 2026-08-09 | UI/UX & Data | • 8종 공시 가상 테스트 데이터 구축 (`samples/*.yaml`, `mock_license_out_contract.txt` 등)<br>• 파일 업로드 시 업로드 문서 기반 동적 AI 인사이트 로그 및 DART/KIND 폼 맵핑 구현<br>• 토스트 알림창 자동 닫힘 제거 및 수동 `✕` 닫기 버튼 적용 | 공시 개발팀 |
| **v1.0.0** | 2026-08-09 | Major Release | • **양식별 Pydantic 법규 검증 레이어 구축** (`api/forms/` 8종 서식 스키마 완비)<br>• **DataSource Protocol 표준 인터페이스 개발** (`data_source.py` 토큰 `${today}` 자동 치환)<br>• **Gemini Tool-Use 멀티턴 에이전트 서비스 연동** (`agent_service.py`) <br>• **Playwright 보안 팝업 자동 디스미스 및 UA 스푸핑 구현** (`browser_service.py`) <br>• **21개 전체 단위 및 통합 테스트 100% 통과 (PASSED)** | 공시 개발팀 |

---

## 🎯 2. 개요 및 목적 (Overview & Goals)

- **사용자(Who):** 
  - **공시 담당자:** 원본 문서 업로드, 초안 검토·수정, 내부 품의 작성, 최종 제출 진행
  - **공시 책임자 / 대표이사:** 최종 승인 및 전자결재
  - **AI 에이전트:** 비정형 문서 데이터 자동 추출, DART XML 매핑, 2단계 스키마 검증, 초안 생성
- **목표(Why):**
  - 공시 작성 과정의 반복적 입력을 자동화하여 작성 시간 단축 및 입력 오류 사전 차단.
  - **Human-in-the-loop 원칙:** 초안 작성과 컴플라이언스 검증은 AI가 보조하되, 최종 제출은 사용자가 공동인증서로 직접 수행하여 효율성과 법적 책임을 동시에 만족.

---

## 🏗️ 3. 시스템 아키텍처 & 핵심 파이프라인

```text
[ 원본 자료 업로드 ] (PDF, Word, Excel, 텍스트)
       │
       ▼
[ Gemini AI 파서 ] ──(Pydantic/YAML 구조화)──▶ [ 1차 검증: Layer-1 (api/forms/) ]
                                                      │ (날짜, 금액, 필수필드, 법규 검증)
                                                      ▼
[ DART .dsd 매퍼 (dsd_service.py) ] ◄──── [ 2차 검증: Layer-2 (dsd_service.py) ]
       │                                        │ (셀 데이터, AUNITVALUE, TR 행보존 검증)
       │                                        │  └─▶ 메모리 캐싱된 templates/dsd/ 사용
       ▼                                              ▼
[ Mode B: 백엔드 .dsd 바이너리 빌드 ]      [ Mode A: KIND 포털 자동화 (browser_service) ]
       │                                        │ (macOS UA 스푸핑, INISAFE 팝업 디스미스)
       └───────────────────┬────────────────────┘
                           ▼
[ Human-in-the-loop Split-View UI ]
 (좌: 실시간 타임스탬프 AI 인사이트 로그 / 우: DART/KIND 폼 편집기 & 수동 ✕ 토스트 알림)
                           │
                           ▼
[ 최종 승인된 .dsd 바이너리 다운로드 및 공동인증서 사용자 직접 제출 ]
```

---

## 🚀 4. 핵심 기능 명세 (Detailed Features)

### 4.1 이중 검증 파이프라인 (Dual-Layer Validation)
- **Layer 1 (비즈니스 및 법규 규칙 검증):** `api/forms/` 내 Pydantic 스키마를 통해 날짜 순서 논리(이사회 결의일 $\le$ 주총 개최일), 주식 수 유효성(부여 주식수 $\le$ 발행주식총수), 금액 범위를 정밀 검증.
- **Layer 2 (DART XML 스키마 검증):** `dsd_service.py`를 통해 DART 편집기가 요구하는 `<TE>`, `<TU>` 셀 빈값 `-` 자동 채움, `AUNITVALUE` 필수 지정, `TR` 행 삭제 방지 검증을 백엔드에서 100% 사전 차단.

### 4.2 DataSource Protocol 추상화
- `DataSourceProtocol` 인터페이스를 구현하여 `YamlDataSource` (토큰 `${today}`, `${random_name_ko}` 동적 치환) ↔ `OpenDartDataSource` ↔ `지식 그래프(KG)` 간 데이터 소스를 상위 코드 수정 없이 자유롭게 스위칭.

### 4.3 Gemini Tool-Use 자율 에이전트 서비스
- `DisclosureAgentService` (`agent_service.py`)를 통해 Gemini AI가 백엔드 툴(`list_dsd_templates`, `read_dsd_template`, `validate_against_template`)을 자율적으로 호출하며 검증 오류를 스스로 수정하고 최적의 공시 초안을 완성.

### 4.4 Playwright 포털 세션 및 보안 팝업 관리
- `BrowserSessionManager` (`browser_service.py`)를 통해 Linux Chromium 환경에서 macOS UA 스푸핑으로 포털 차단을 우회하고, INISAFE/8단계 안내 팝업(`_AUTO_CLOSE_URL_SUBSTRINGS`)을 자동 디스미스하며, `.env` 자격증명(`KRX_ID`, `KRX_PW`)을 안전하게 입력 (`fill_secret`).

### 4.5 Modern Web UI 및 UX 개선
- **Split-View 레이아웃:** 좌측(실시간 타임스탬프 AI 인사이트 로그) / 우측(DART/KIND 폼 편집기).
- **동적 파싱 반영:** 선택한 공시 문서에 맞추어 실제 금액, 날짜, 서식 종류가 실시간 맵핑.
- **수동 ✕ 닫기 토스트 알림:** 알림 메시지가 자동으로 닫히지 않고 사용자가 직접 `✕` 버튼을 누를 때만 사라지도록 안정성 강화.

---

## 🔌 5. API 명세 (REST Endpoints)

| 엔드포인트 | 메서드 | 설명 | 비고 |
| :--- | :--- | :--- | :--- |
| `/upload` | `POST` | 원본 공시 문서(PDF/DOCX/XLSX) 업로드 및 Gemini 파싱 | multipart/form-data |
| `/validate` | `POST` | 공시 필드 1차 법규 검증 및 2차 DART XML 스키마 검증 | JSON payload |
| `/api/templates` | `GET` | 사용 가능한 `.dsd` 템플릿 목록 조회 | JSON response |
| `/api/templates/build` | `POST` | XML 파싱 데이터를 검증 후 `.dsd` 바이너리 ZIP 파일로 바로 반환 | attachment download |
| `/health` | `GET` | 서버 헬스체크 및 환경 설정 상태 반환 | 시스템 모니터링 |

---

## 🧪 6. 품질 보증 및 테스트 결과 (QA & Verification)

### 단위 및 통합 테스트 (Pytest 100% 통과)
```powershell
py -m pytest tests/ -v
```

- `tests/test_browser_service.py` **PASSED** (INISAFE 팝업 디스미스 & 화이트리스트 검증)
- `tests/test_data_source.py` **PASSED** (DataSource Protocol 및 YAML 토큰 치환 검증)
- `tests/test_dsd_service.py` **PASSED** (XML 2차 스키마 검증, Zip 메모리 생성 검증)
- `tests/test_forms.py` **PASSED** (Pydantic 양식별 법규 검증 모델 검증)
- `tests/test_mock_disclosures.py` **PASSED** (8종 가상 공시 데이터 연동 검증)

**총 21개 테스트 100% PASSED (0 Failures)**
