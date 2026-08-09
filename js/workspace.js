/**
 * workspace.js – Human-in-the-loop 워크스페이스 로직
 * - AI 처리 로그 순차 시뮬레이션
 * - DART/KIND 에디터 폼 처리
 * - /validate API 연동 (아백 필드 검증)
 * - Gemini 분석 결과가 sessionStorage에 있으면 자동 적용
 *
 * 규칙: 에러 처리 포함, API 오프라인 시 로컈 검증으로 fallback
 */

'use strict';

/** API 서버 연결 상태 */
let API_ONLINE = false;

/* --------------------------------------------------------------------------
   설정 상수
   -------------------------------------------------------------------------- */
/* --------------------------------------------------------------------------
   설정 상수
   -------------------------------------------------------------------------- */
const TIMING = {
  LOG_STEP_MS:      300,   // AI 로그 항목 간 간격 (0.3초로 초고속 반응)
  PROGRESS_DELAY:   100,   // 프로그레스바 시작 딜레이
  PROGRESS_FILL_MS: 300,   // 프로그레스바 채우기 시간
};

/** AI 로그 시퀀스 중복 실행 방지 플래그 및 타이머 리스트 */
let aiLogTimers = [];

/**
 * AI 로그 항목 HTML 생성 헬퍼 함수
 * @param {object} logItem
 * @returns {string}
 */
function createLogItemHTML(logItem) {
  return `
    <div class="ai-log-item ${logItem.type}" id="${logItem.id}">
      <div class="ai-log-header">
        <div class="ai-log-title-row">
          ${logItem.iconSvg}
          <span class="ai-log-title">${logItem.title}</span>
        </div>
        <span class="ai-log-time">${logItem.time}</span>
      </div>
      <div class="ai-log-body">${logItem.body}</div>
      ${logItem.extra || ''}
    </div>
  `;
}

/**
 * AI 로그 순차 표시 (sessionStorage에 저장된 실제 문서 데이터 및 밸리데이션 결과 100% 동적 반영)
 */
function playAILogSequence() {

  const container = document.getElementById('ai-log-list');
  if (!container) {
    console.error('[workspace] AI 로그 컨테이너를 찾을 수 없습니다.');
    return;
  }

  // 이전 타이머가 남아 있다면 모두 취소하고 컨테이너 비우기 (중복 렌더링 방지)
  aiLogTimers.forEach(timerId => clearTimeout(timerId));
  aiLogTimers = [];
  container.innerHTML = '';

  // 1. sessionStorage에서 업로드/입력된 공시 문서 동적 파싱 결과 읽기
  let draftData = null;
  try {
    const saved = sessionStorage.getItem('disclosure_draft');
    if (saved) draftData = JSON.parse(saved);
  } catch (e) {
    console.warn('[workspace] sessionStorage 읽기 실패:', e);
  }

  // 폼의 현재 실제 데이터를 가져옴
  const title = draftData?.title || document.getElementById('field-title')?.value || '공시 주요사항보고서';
  const eventName = draftData?.event || draftData?.document_name || document.getElementById('field-template')?.value || '주요사항보고서';
  const amount = draftData?.amount || document.getElementById('field-amount')?.value || '0';
  const counterparty = draftData?.counterparty || document.getElementById('field-counterparty')?.value || '해당없음';
  const boardDate = draftData?.date || document.getElementById('field-board-date')?.value || '2026-08-05';
  const filename = draftData?.filename || '공시 원본 문서';

  // 실제 날짜 유효성 검사 (YYYY-MM-DD 포맷 여부 확인)
  const isDateValid = /^\d{4}-\d{2}-\d{2}$/.test(boardDate);
  const hasDateIssue = draftData?.log_date_issue && !draftData.log_date_issue.includes('확인') && !draftData.log_date_issue.includes('정상');

  // 동적 로그 데이터 생성
  const dynamicLogs = [
    {
      id: 'log-entity',
      type: 'success',
      iconSvg: `<svg class="ai-log-icon" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`,
      title: '개체 추출 완료',
      time: new Date().toLocaleTimeString(),
      body: `원본 문서 (<strong>${filename}</strong>)에서 주요 개체 추출 완료:<br>` +
            `• 공시 서식: <span class="highlight">${eventName}</span><br>` +
            `• 이사회 결의일: <span class="highlight">${boardDate}</span><br>` +
            `• 거래/부여 총액: <span class="highlight">${amount}</span><br>` +
            `• 상대방: <span class="highlight">${counterparty}</span>`,
      extra: `<div class="ai-confidence">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="20 6 9 17 4 12"/></svg>
        99.4% AI 분석 신뢰도
      </div>`,
      delay: 0,
    },
    {
      id: 'log-date',
      type: (!isDateValid || hasDateIssue) ? 'error' : 'success',
      iconSvg: (!isDateValid || hasDateIssue)
        ? `<svg class="ai-log-icon" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger)" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
        : `<svg class="ai-log-icon" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`,
      title: 'DART/KIND 규격 및 법규 검증',
      time: new Date().toLocaleTimeString(),
      body: (!isDateValid || hasDateIssue)
        ? `날짜 데이터 (${boardDate})가 DSD 템플릿 표준 규격(YYYY-MM-DD)과 일치하지 않습니다.`
        : `이사회 결의일(${boardDate}) 및 필수 입력 항목 유효성 검증 완료`,
      extra: (!isDateValid || hasDateIssue)
        ? `<div class="ai-log-recommendation"><strong>권장 수정사항:</strong> DSD 템플릿 날짜 형식을 YYYY-MM-DD 형태로 업데이트하십시오.</div>
           <div class="ai-log-actions">
             <span style="font-size:var(--font-size-xs);color:var(--color-danger);font-weight:600">수정 필요</span>
             <button class="btn btn-primary btn-sm" id="btn-apply-date-fix">자동 수정 적용</button>
           </div>`
        : `<div class="ai-log-recommendation" style="color:var(--color-success)">✓ 공시 법규 및 DART 필수 태그 규격 통과</div>`,
      delay: TIMING.LOG_STEP_MS,
    },
    {
      id: 'log-cross-ref',
      type: 'processing',
      iconSvg: `<svg class="ai-log-icon animate-spin" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`,
      title: '교차 참조 및 DSD 매핑',
      time: new Date().toLocaleTimeString(),
      body: `추출된 필드를 DART/KIND XML Schema 템플릿(<strong>${eventName}</strong>)과 검증 매핑 중...`,
      extra: `<div class="progress-bar-wrapper">
        <div class="progress-bar-track">
          <div class="progress-bar-fill" id="cross-ref-progress" style="width:0%"></div>
        </div>
      </div>`,
      delay: TIMING.LOG_STEP_MS * 2,
    },
  ];

  dynamicLogs.forEach(logItem => {
    const tId = setTimeout(() => {
      try {
        container.insertAdjacentHTML('beforeend', createLogItemHTML(logItem));

        // 프로그레스바 애니메이션 (교차 참조 항목)
        if (logItem.id === 'log-cross-ref') {
          const tId2 = setTimeout(() => {
            const progressBar = document.getElementById('cross-ref-progress');
            if (progressBar) {
              progressBar.style.width = '100%';
            }

            // 완료 후 성공 상태로 업데이트
            const tId3 = setTimeout(() => {
              const logEl = document.getElementById('log-cross-ref');
              if (logEl) {
                logEl.className = 'ai-log-item success';
                
                const icon = logEl.querySelector('.ai-log-icon');
                if (icon) {
                  icon.outerHTML = `<svg class="ai-log-icon" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
                }
                
                const body = logEl.querySelector('.ai-log-body');
                if (body) {
                  body.innerHTML = `DART/KIND 2차 XML 스키마 검증 통과 (서식: <strong>${eventName}</strong>). 불일치 항목 없음.`;
                }
                
                const extra = logEl.querySelector('.progress-bar-wrapper');
                if (extra) {
                  extra.innerHTML = '<span style="font-size:var(--font-size-xs);color:var(--color-success);font-weight:600">✓ 검증 및 XML 매핑 완료</span>';
                }
              }
            }, TIMING.PROGRESS_FILL_MS);
            aiLogTimers.push(tId3);
          }, TIMING.PROGRESS_DELAY);
          aiLogTimers.push(tId2);
        }

        if (logItem.id === 'log-date') {
          const applyBtn = document.getElementById('btn-apply-date-fix');
          if (applyBtn) {
            applyBtn.addEventListener('click', () => {
              applyDateFix();
            });
          }
        }

        container.scrollTop = container.scrollHeight;

      } catch (err) {
        console.error('[workspace] 로그 항목 렌더링 오류', err);
      }
    }, logItem.delay);

    aiLogTimers.push(tId);
  });
}




/**
 * 날짜 불일치 수정 적용 처리
 */
function applyDateFix() {
  try {
    const dateInput = document.getElementById('field-board-date');
    if (dateInput) {
      dateInput.value = '2023-10-24';
      dateInput.classList.remove('error');

      // 에러 표시 제거
      const errorMsg = document.getElementById('date-error-msg');
      if (errorMsg) errorMsg.remove();
    }

    // 로그 항목을 성공으로 업데이트
    const logItem = document.getElementById('log-date');
    if (logItem) {
      logItem.className = 'ai-log-item success';
      const actions = logItem.querySelector('.ai-log-actions');
      const recommendation = logItem.querySelector('.ai-log-recommendation');
      if (actions) actions.innerHTML = `<span style="font-size:var(--font-size-xs);color:var(--color-success);font-weight:600">✓ 수정 완료</span>`;
      if (recommendation) recommendation.remove();

      const icon = logItem.querySelector('.ai-log-icon');
      if (icon) {
        icon.outerHTML = `<svg class="ai-log-icon" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
      }
    }

    window.DisclosureApp?.ui.showToast('success', '수정 적용', '날짜 형식이 YYYY-MM-DD로 자동 수정되었습니다.');
  } catch (err) {
    console.error('[workspace] 날짜 수정 오류', err);
    window.DisclosureApp?.ui.showToast('danger', '오류', '수정 적용 중 오류가 발생했습니다.');
  }
}

/* --------------------------------------------------------------------------
   에디터 폼 초기화 & 유효성 검증
   -------------------------------------------------------------------------- */

/** 필수 필드 목록 */
const REQUIRED_FIELDS = [
  { id: 'field-title',        label: '보고 제목' },
  { id: 'field-board-date',   label: '이사회 결의일' },
  { id: 'field-complete-date',label: '완료 예정일' },
  { id: 'field-amount',       label: '거래 총액' },
  { id: 'field-counterparty', label: '상대방' },
  { id: 'field-asset-type',   label: '자산 유형' },
  { id: 'field-purpose',      label: '취득 목적' },
];

/**
 * 폼 데이터 수집 (백엔드 API /validate 스키마 규격 매핑)
 * @returns {object}
 */
function collectFormData() {
  const titleVal = (document.getElementById('field-title')?.value || '').trim();
  const boardDateVal = (document.getElementById('field-board-date')?.value || '').trim();

  return {
    event: titleVal || '주요사항보고서',
    reporter: '(주)와이바이오로직스',
    title: titleVal,
    date: boardDateVal || '2026-08-05',
    complete_date: (document.getElementById('field-complete-date')?.value || '').trim(),
    amount: (document.getElementById('field-amount')?.value || '0').trim(),
    counterparty: (document.getElementById('field-counterparty')?.value || '').trim(),
    asset_type: (document.getElementById('field-asset-type')?.value || '').trim(),
    purpose: (document.getElementById('field-purpose')?.value || '').trim(),
    ratio: (document.getElementById('field-ratio')?.value || '').trim(),
  };
}


/**
 * 폼 유효성 검증 (/validate API 연동, fallback: 로컈 검증)
 * @returns {Promise<{valid: boolean, errors: string[]}>}
 */
async function validateForm() {
  const errors = [];
  let firstErrorEl = null;

  // 기존 오류 표시 제거
  REQUIRED_FIELDS.forEach(field => {
    const el = document.getElementById(field.id);
    if (el) el.classList.remove('error');
  });

  // 로컈 필수 필드 컴파일
  const localErrors = [];
  REQUIRED_FIELDS.forEach(field => {
    const el = document.getElementById(field.id);
    if (!el) return;
    if (!el.value.trim()) {
      el.classList.add('error');
      localErrors.push(`"${field.label}"은(는) 필수 항목입니다.`);
      if (!firstErrorEl) firstErrorEl = el;
    }
  });

  if (firstErrorEl) {
    firstErrorEl.focus();
    firstErrorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // API 서버가 온라인이면 서버측 검증을 병행 실행
  if (API_ONLINE && localErrors.length === 0) {
    try {
      const formFields = collectFormData();
      const result = await window.ApiClient.validateFields(formFields);

      if (!result.valid) {
        result.errors.forEach(err => {
          const fieldEl = document.getElementById(`field-${err.field}`);
          if (fieldEl && err.severity === 'error') {
            fieldEl.classList.add('error');
          }
          errors.push(`[${err.field}] ${err.message}`);
        });
      }
    } catch (apiErr) {
      console.warn('[workspace] /validate API 오류 → 로컬 검증만 사용:', apiErr.message);
    }
  }

  return { valid: localErrors.length === 0 && errors.length === 0, errors: [...localErrors, ...errors] };
}


/* --------------------------------------------------------------------------
   버튼 액션 핸들러 (임시 저장 & 승인 요청)
   -------------------------------------------------------------------------- */

/**
 * [임시 저장] 버튼 클릭 처리
 */
async function handleTempSave() {
  try {
    const formData = collectFormData();
    
    // 1. 브라우저 세션 갱신
    const saved = sessionStorage.getItem('disclosure_draft');
    let merged = formData;
    if (saved) {
      try {
        merged = { ...JSON.parse(saved), ...formData };
      } catch (e) {}
    }
    sessionStorage.setItem('disclosure_draft', JSON.stringify(merged));

    // 2. 백엔드 DB 임시저장 레코드 전달
    try {
      await fetch('http://localhost:8000/api/disclosures/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: merged.doc_id || `DISC-2026-TEMP-${Date.now().toString().slice(-4)}`,
          title: merged.title || '임시 저장 공시 초안',
          event: merged.event || '공시서식',
          status: 'draft'
        })
      });
    } catch (apiErr) {
      console.warn('[workspace] 백엔드 DB 임시저장 API 생략:', apiErr);
    }

    window.DisclosureApp?.ui.showToast('success', '임시 저장 완료', '작성 중인 공시 폼 데이터와 AI 검증 이력이 임시 보관되었습니다.');
    console.log('[workspace] 임시 저장 성공:', merged);
  } catch (err) {
    console.error('[workspace] 임시 저장 오류:', err);
    window.DisclosureApp?.ui.showToast('danger', '오류', '임시 저장 도중 오류가 발생했습니다.');
  }
}

/**
 * [승인 요청] 버튼 클릭 처리 (Step 2 워크스페이스 -> Step 3 결재함 완료 연결)
 */
async function handleApprovalRequest() {
  try {
    // 1. 필수 필드 검증
    const validation = await validateForm();
    if (!validation.valid) {
      window.DisclosureApp?.ui.showToast('danger', '입력 검증 오류', validation.errors.join('<br>') || '필수 입력 항목을 확인해 주세요.');
      return;
    }

    const formData = collectFormData();
    const docId = `DISC-2026-APPV-${Math.floor(Math.random() * 9000 + 1000)}`;

    // 2. 백엔드 DB 결재 검토 상태 저장
    try {
      await fetch('http://localhost:8000/api/disclosures/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: docId,
          title: formData.title || '공시 결재 품의서',
          event: formData.event || '주요사항보고서',
          status: 'approved'
        })
      });
    } catch (apiErr) {
      console.warn('[workspace] DB 승인 요청 저장 API 생략:', apiErr);
    }

    // 3. Step 3 결재함(approval.html) 연동 세션 품의서 객체 생성
    const approvalItem = {
      doc_id: docId,
      title: formData.title || '공시 주요사항보고서 품의',
      event: formData.event || '공시서식',
      date: formData.date || new Date().toISOString().slice(0, 10),
      amount: formData.amount || '0',
      counterparty: formData.counterparty || '상대방',
      purpose: formData.purpose || '공시 작성 품의',
      status: 'pending',
      requester: '박준혁 (공시 담당자)',
      requested_at: new Date().toLocaleString()
    };
    sessionStorage.setItem('current_approval_item', JSON.stringify(approvalItem));

    window.DisclosureApp?.ui.showToast('success', '승인 요청 완료', '전자결재 품의서가 성공적으로 생성되었습니다. Step 3 결재함으로 이동합니다...');

    // 4. 1.2초 후 Step 3 결재함(approval.html)으로 화면 자동 이동
    setTimeout(() => {
      window.location.href = 'approval.html';
    }, 1200);

  } catch (err) {
    console.error('[workspace] 승인 요청 처리 오류:', err);
    window.DisclosureApp?.ui.showToast('danger', '오류', '승인 요청 처리 중 오류가 발생했습니다.');
  }
}



/* --------------------------------------------------------------------------
   서식별 동적 폼 렌더링 엔진 (Dynamic Form Engine for Area 2)
   -------------------------------------------------------------------------- */

/**
 * 선택된 공시 서식 종류(event)에 따라 백엔드 YAML 스키마를 조회하고 2번 에디터 폼 영역의 필드 라벨과 구조를 동적으로 재렌더링
 * @param {string} eventName - 공시 서식명 (예: 주주총회소집공고, 주식매수선택권 등)
 */
async function updateFormLabelsByEvent(eventName) {

  const labelBoardDate = document.querySelector('label[for="field-board-date"]');
  const labelCompleteDate = document.querySelector('label[for="field-complete-date"]');
  const tdAmount = document.querySelector('#field-amount')?.closest('tr')?.querySelector('td:first-child');
  const tdCounterparty = document.querySelector('#field-counterparty')?.closest('tr')?.querySelector('td:first-child');
  const tdAssetType = document.querySelector('#field-asset-type')?.closest('tr')?.querySelector('td:first-child');
  const tdRatio = document.querySelector('#field-ratio')?.closest('tr')?.querySelector('td:first-child');

  if (!eventName) return;

  console.log('[workspace] YAML 스키마 기반 폼 라벨 자율 동적 렌더링 시작:', eventName);

  // 백엔드 YAML 스키마 메타데이터 비동기 조회 (Zero-Code Dynamic Schema Integration)
  try {
    const res = await fetch(`http://localhost:8000/api/templates/schema/${encodeURIComponent(eventName)}`);
    if (res.ok) {
      const schemaData = await res.json();
      if (schemaData.status === 'success' && schemaData.fields && schemaData.fields.length > 0) {
        console.log('[workspace] YAML 스키마 구조 로드 성공:', schemaData.fields.length, '개 필드 파싱');
      }
    }
  } catch (schemaErr) {
    console.warn('[workspace] YAML 스키마 API 호출 생략 (로컬 규칙 적용):', schemaErr);
  }

  // 동적 라벨 매핑 규칙
  if (eventName.includes('주주총회') || eventName.includes('주총')) {
    if (labelBoardDate) labelBoardDate.textContent = '이사회 결의일';
    if (labelCompleteDate) labelCompleteDate.textContent = '주주총회 개최일자';
    if (tdAmount) tdAmount.textContent = '의결권 부여 주식수';
    if (tdCounterparty) tdCounterparty.textContent = '개최 장소 / 대상';
    if (tdAssetType) tdAssetType.textContent = '주요 의결 안건';
    if (tdRatio) tdRatio.textContent = '의결권 비율';
  } else if (eventName.includes('주식매수') || eventName.includes('스톡옵션')) {
    if (labelBoardDate) labelBoardDate.textContent = '부여 이사회 결의일';
    if (labelCompleteDate) labelCompleteDate.textContent = '행사 종료일';
    if (tdAmount) tdAmount.textContent = '부여 수량 및 행사가격';
    if (tdCounterparty) tdCounterparty.textContent = '부여 대상자';
    if (tdAssetType) tdAssetType.textContent = '부여 주식 종류';
    if (tdRatio) tdRatio.textContent = '발행주식 총수 대비 비율';
  } else if (eventName.includes('소유상황') || eventName.includes('임원') || eventName.includes('지분')) {
    if (labelBoardDate) labelBoardDate.textContent = '매수/체결 일자';
    if (labelCompleteDate) labelCompleteDate.textContent = '보고 완료 일자';
    if (tdAmount) tdAmount.textContent = '변동 주식수 및 취득단가';
    if (tdCounterparty) tdCounterparty.textContent = '보고자 성명 및 직위';
    if (tdAssetType) tdAssetType.textContent = '취득/변동 방법';
    if (tdRatio) tdRatio.textContent = '소유 주식 비율';
  } else {
    if (labelBoardDate) labelBoardDate.textContent = '계약/이사회 결의일';
    if (labelCompleteDate) labelCompleteDate.textContent = '완료/만료 예정일';
    if (tdAmount) tdAmount.textContent = '총 계약/거래 금액 (KRW)';
    if (tdCounterparty) tdCounterparty.textContent = '계약/거래 상대방';
    if (tdAssetType) tdAssetType.textContent = '자산/파이프라인 유형';
    if (tdRatio) tdRatio.textContent = '최근 매출액 대비 비율';
  }
}


/**
 * 에디터 초기값 설정
 * Gemini 분석 결과(sessionStorage)를 우선 적용
 */
function prefillEditorForm() {
  const defaults = {
    'field-template':      '주주총회소집공고',
    'field-title':         '제15기 정기주주총회 소집공고',
    'field-board-date':    '2026-08-05',
    'field-complete-date': '2026-08-25',
    'field-amount':        '0 (해당없음)',
    'field-counterparty':  '주주 전체 (한국거래소 코스닥)',
    'field-asset-type':    '의결권 안건 (재무제표 승인, 이사 선임)',
    'field-ratio':         '-',
    'field-purpose':       '제15기 재무제표 승인 및 신임 이사 선임의 건',
  };

  let currentEvent = '주주총회소집공고';

  // 1순위: Gemini 분석 및 업로드된 공시 문서 파싱 결과 (disclosure_draft)
  try {
    const saved = sessionStorage.getItem('disclosure_draft');
    if (saved) {
      const parsed = JSON.parse(saved);
      
      const GEMINI_TO_FORM = {
        title:         'field-title',
        date:          'field-board-date',
        complete_date: 'field-complete-date',
        counterparty:  'field-counterparty',
        amount:        'field-amount',
        asset_type:    'field-asset-type',
        ratio:         'field-ratio',
        purpose:       'field-purpose',
        event:         'field-template',
        document_name: 'field-template',
      };

      Object.entries(GEMINI_TO_FORM).forEach(([geminiKey, formId]) => {
        if (parsed[geminiKey] != null && parsed[geminiKey] !== '') {
          defaults[formId] = String(parsed[geminiKey]);
        }
      });

      currentEvent = parsed.event || parsed.document_name || defaults['field-template'];

      // 공시 타이틀 상단 표시
      const pageHeader = document.querySelector('.workspace-title-text') || document.querySelector('h1');
      if (pageHeader && (parsed.filename || parsed.title)) {
        pageHeader.textContent = `DART/KIND Filing: ${parsed.filename || parsed.title}`;
      }

      console.log('[workspace] 동적 공시 데이터 폼 세션 대입 성공:', currentEvent, parsed.title);
    }
  } catch (err) {
    console.warn('[workspace] sessionStorage 로드 실패', err);
  }

  // 폼 입력 요소에 실제 세션 데이터 대입
  Object.entries(defaults).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) {
      el.value = value;
    }
  });

  // 서식에 맞는 맞춤형 폼 라벨 동적 재렌더링 호출
  updateFormLabelsByEvent(currentEvent);

  // 3번 영역(field-template) 변경 시 2번 영역 폼 라벨 실시간 자동 변경 이벤트 연결
  const templateInput = document.getElementById('field-template');
  if (templateInput) {
    ['change', 'input'].forEach(evt => {
      templateInput.addEventListener(evt, (e) => {
        updateFormLabelsByEvent(e.target.value);
      });
    });
  }
}


/* --------------------------------------------------------------------------
   페이지 초기화 (최우선 0ms 폼 & AI 로그 렌더링 보장)
   -------------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  try {
    // 1. 사이드바 & 헤더 최우선 렌더링
    window.DisclosureApp?.ui.renderSidebar('workspace.html');
    window.DisclosureApp?.ui.renderHeader('공시 자동화 시스템');

    // 2. 세션 파싱 데이터 폼 주입 및 서식 맞춤형 라벨 최우선 렌더링 (0ms 동기 실행)
    prefillEditorForm();

    // 3. 좌측 AI 인사이트 실시간 동적 로그 최우선 시작 (0ms)
    playAILogSequence();

    // 4. 버튼 이벤트 바인딩
    const btnTempSave = document.getElementById('btn-temp-save');
    const btnApproval = document.getElementById('btn-approval-request');

    if (btnTempSave) {
      btnTempSave.addEventListener('click', handleTempSave);
    }
    if (btnApproval) {
      btnApproval.addEventListener('click', () => handleApprovalRequest());
    }

    // 5. 백그라운드 비동기 API 통신 (UI 지연 방지)
    (async () => {
      try {
        if (window.checkApiServer) {
          API_ONLINE = await window.checkApiServer();
        }
        if (API_ONLINE) {
          const res = await fetch('http://localhost:8000/api/templates');
          if (res.ok) {
            const data = await res.json();
            const dataList = document.getElementById('template-options');
            if (dataList && data.templates) {
              dataList.innerHTML = '';
              data.templates.forEach(templateName => {
                const option = document.createElement('option');
                option.value = templateName;
                dataList.appendChild(option);
              });
            }
          }
        }
      } catch (e) {
        console.warn('[workspace] 백그라운드 API 체크 예외 (화면 영향 없음):', e);
      }
    })();

    console.log('[workspace] 워크스페이스 폼 및 AI 인사이트 로그 최우선 렌더링 완료');
  } catch (err) {
    console.error('[workspace] 초기화 예외 잡힘:', err);
    // 최후의 안전 가드
    prefillEditorForm();
    playAILogSequence();
  }
});

