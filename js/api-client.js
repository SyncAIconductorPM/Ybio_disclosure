/**
 * js/api-client.js – 백엔드 API 호출 모듈
 * FastAPI 서버(localhost:8000)와 통신하는 fetch 래퍼입니다.
 *
 * 규칙: 에러 처리 포함, BASE_URL 하드코딩 금지 (API_CONFIG 사용)
 */

'use strict';

/* --------------------------------------------------------------------------
   API 설정 (환경 변수 역할 — 빌드 시 교체 가능)
   -------------------------------------------------------------------------- */
const API_CONFIG = {
  BASE_URL:        'http://localhost:8000',
  REQUEST_TIMEOUT: 60_000,   // 60초 (Gemini 처리 시간 고려)
  RETRY_COUNT:     1,
};

/* --------------------------------------------------------------------------
   내부 유틸리티
   -------------------------------------------------------------------------- */

/**
 * 타임아웃이 있는 fetch
 * @param {string} url
 * @param {RequestInit} options
 * @param {number} [timeoutMs]
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = API_CONFIG.REQUEST_TIMEOUT) {
  const controller = new AbortController();
  const timerId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timerId);
  }
}

/**
 * API 응답 처리 공통 함수
 * @param {Response} response
 * @returns {Promise<any>}
 * @throws {Error} HTTP 오류 또는 JSON 파싱 오류
 */
async function handleResponse(response) {
  let body;
  try {
    body = await response.json();
  } catch {
    body = { detail: `응답 파싱 실패 (HTTP ${response.status})` };
  }

  if (!response.ok) {
    const detail = body?.detail || `HTTP 오류: ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

/* --------------------------------------------------------------------------
   공개 API 클라이언트
   -------------------------------------------------------------------------- */

const ApiClient = {

  /**
   * 서버 헬스체크
   * @returns {Promise<{status: string, gemini_model: string}>}
   */
  async health() {
    try {
      const resp = await fetchWithTimeout(`${API_CONFIG.BASE_URL}/health`, {}, 5000);
      return handleResponse(resp);
    } catch (err) {
      throw new Error(`API 서버에 연결할 수 없습니다. (${err.message})`);
    }
  },

  // ── 업로드 & 파싱 ─────────────────────────────────────────────────────

  /**
   * 파일 업로드 및 AI 필드 추출
   * @param {File} file - PDF/DOCX/XLSX 파일
   * @param {(progress: number) => void} [onProgress] - 진행률 콜백 (0~100)
   * @returns {Promise<{doc_id: string, fields: object, yaml_str: string}>}
   */
  async uploadDocument(file, onProgress) {
    if (!file) throw new Error('파일이 없습니다.');

    const formData = new FormData();
    formData.append('file', file);

    // 진행 시작 알림
    onProgress?.(10);

    try {
      const resp = await fetchWithTimeout(
        `${API_CONFIG.BASE_URL}/upload`,
        { method: 'POST', body: formData }
      );
      onProgress?.(90);
      const result = await handleResponse(resp);
      onProgress?.(100);
      return result;
    } catch (err) {
      console.error('[api-client] 업로드 오류:', err);
      throw err;
    }
  },

  /**
   * 텍스트 직접 파싱
   * @param {string} text - 분석할 텍스트
   * @returns {Promise<{doc_id: string, fields: object, yaml_str: string}>}
   */
  async parseText(text) {
    if (!text?.trim()) throw new Error('텍스트가 비어 있습니다.');

    const resp = await fetchWithTimeout(
      `${API_CONFIG.BASE_URL}/upload/parse`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      }
    );
    return handleResponse(resp);
  },

  // ── 유효성 검증 ──────────────────────────────────────────────────────

  /**
   * 공시 필드 유효성 검증
   * @param {object} fields - 검증할 필드 딕셔너리
   * @returns {Promise<{valid: boolean, errors: Array, error_count: number}>}
   */
  async validateFields(fields) {
    if (!fields || typeof fields !== 'object') throw new Error('유효한 필드 객체가 필요합니다.');

    const resp = await fetchWithTimeout(
      `${API_CONFIG.BASE_URL}/validate`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields }),
      }
    );
    return handleResponse(resp);
  },

  // ── OpenDART ─────────────────────────────────────────────────────────

  /**
   * 기업 기본 정보 조회
   * @param {string} corpCode - 8자리 OpenDART 기업 고유번호
   * @returns {Promise<object>}
   */
  async getCompany(corpCode) {
    if (!corpCode) throw new Error('corp_code가 필요합니다.');

    const url = new URL(`${API_CONFIG.BASE_URL}/dart/company`);
    url.searchParams.set('corp_code', corpCode);

    const resp = await fetchWithTimeout(url.toString());
    return handleResponse(resp);
  },

  /**
   * 공시 목록 조회
   * @param {string} corpCode
   * @param {object} [options] - { bgn_de, end_de, page_no, page_count }
   * @returns {Promise<{total_count: number, list: Array}>}
   */
  async getDisclosures(corpCode, options = {}) {
    if (!corpCode) throw new Error('corp_code가 필요합니다.');

    const url = new URL(`${API_CONFIG.BASE_URL}/dart/disclosures`);
    url.searchParams.set('corp_code', corpCode);
    if (options.bgn_de)     url.searchParams.set('bgn_de',     options.bgn_de);
    if (options.end_de)     url.searchParams.set('end_de',     options.end_de);
    if (options.page_no)    url.searchParams.set('page_no',    options.page_no);
    if (options.page_count) url.searchParams.set('page_count', options.page_count);

    const resp = await fetchWithTimeout(url.toString());
    return handleResponse(resp);
  },

  /**
   * 회사명으로 기업 검색
   * @param {string} query - 검색어 (2자 이상)
   * @returns {Promise<Array>}
   */
  async searchCompany(query) {
    if (!query || query.length < 2) throw new Error('검색어는 2자 이상이어야 합니다.');

    const url = new URL(`${API_CONFIG.BASE_URL}/dart/search`);
    url.searchParams.set('q', query);

    const resp = await fetchWithTimeout(url.toString());
    return handleResponse(resp);
  },

  // ── KIND 자동화 ──────────────────────────────────────────────────────

  /**
   * KIND 포털 환경 상태 확인
   * @returns {Promise<{playwright_available: boolean, message: string}>}
   */
  async getKindStatus() {
    const resp = await fetchWithTimeout(`${API_CONFIG.BASE_URL}/kind/status`, {}, 10_000);
    return handleResponse(resp);
  },

  /**
   * KIND 양식 자동 입력
   * @param {string} templateName - 공시 양식 이름
   * @param {object} formData - 입력할 필드 데이터
   * @returns {Promise<{status: string, message: string, screenshot: string, filled_count: number}>}
   */
  async prefillKind(templateName, formData) {
    if (!templateName) throw new Error('template_name이 필요합니다.');
    if (!formData || !Object.keys(formData).length) throw new Error('form_data가 비어 있습니다.');

    const resp = await fetchWithTimeout(
      `${API_CONFIG.BASE_URL}/kind/prefill`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_name: templateName, form_data: formData }),
      },
      120_000  // KIND 자동화는 최대 2분
    );
    return handleResponse(resp);
  },
};

/* --------------------------------------------------------------------------
   서버 연결 상태 체크 (페이지 로드 시)
   -------------------------------------------------------------------------- */
async function checkApiServer() {
  try {
    const health = await ApiClient.health();
    console.log('[api-client] 서버 연결 성공:', health);
    return true;
  } catch (err) {
    console.warn('[api-client] API 서버 오프라인 – Mock 모드로 실행:', err.message);
    return false;
  }
}

/* --------------------------------------------------------------------------
   전역 공개
   -------------------------------------------------------------------------- */
window.ApiClient = ApiClient;
window.checkApiServer = checkApiServer;
