/**
 * app.js – 공통 유틸리티, 내비게이션, 상태 관리
 * 공시업무 자동화 시스템 (Human-in-the-loop)
 *
 * 규칙: 에러 처리 포함, 하드코딩 금지 (환경 설정은 APP_CONFIG 사용)
 */

'use strict';

/* --------------------------------------------------------------------------
   앱 전역 설정 (환경 변수 역할)
   -------------------------------------------------------------------------- */
const APP_CONFIG = {
  APP_NAME: 'Disclosure AI',
  APP_SUBTITLE: 'Automated Validation',
  TOAST_DURATION_MS: 4000,
  ROUTES: {
    DASHBOARD: 'index.html',
    WORKSPACE: 'workspace.html',
    APPROVAL:  'approval.html',
    SUBMIT:    'submit.html',
  },
  NAV_ITEMS: [
    { id: 'nav-dashboard', label: '대시보드',     icon: 'grid',    href: 'index.html',     badge: null },
    { id: 'nav-workspace', label: '워크스페이스', icon: 'file',    href: 'workspace.html', badge: null },
    { id: 'nav-history',   label: '히스토리',     icon: 'clock',   href: 'history.html',   badge: null },
    { id: 'nav-template',  label: '템플릿',       icon: 'file',    href: 'template.html',  badge: null },
    { id: 'nav-approval',  label: '결재함',       icon: 'check',   href: 'approval.html',  badge: null },

    { id: 'nav-settings',  label: '설정',         icon: 'settings',href: 'settings.html',  badge: null },
  ],
};

/* --------------------------------------------------------------------------
   SVG 아이콘 라이브러리 (인라인 SVG)
   -------------------------------------------------------------------------- */
const ICONS = {
  grid: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  file: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
  check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 1.42 13.6M4.93 4.93A10 10 0 0 0 3.51 18.53"/><path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>`,
  plus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
  help: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  shield: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  logo: `<svg viewBox="0 0 24 24" fill="white"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>`,
};

/* --------------------------------------------------------------------------
   유틸리티 함수
   -------------------------------------------------------------------------- */

/**
 * 안전한 DOM 요소 선택
 * @param {string} selector - CSS 선택자
 * @param {Element} [context=document] - 검색 컨텍스트
 * @returns {Element|null}
 */
function qs(selector, context = document) {
  try {
    return context.querySelector(selector);
  } catch (err) {
    console.error(`[app] DOM 선택 오류: ${selector}`, err);
    return null;
  }
}

/**
 * 안전한 DOM 요소 다중 선택
 * @param {string} selector
 * @param {Element} [context=document]
 * @returns {NodeList}
 */
function qsa(selector, context = document) {
  try {
    return context.querySelectorAll(selector);
  } catch (err) {
    console.error(`[app] DOM 다중 선택 오류: ${selector}`, err);
    return [];
  }
}

/**
 * 현재 페이지 파일명 반환
 * @returns {string}
 */
function getCurrentPage() {
  const path = window.location.pathname;
  const page = path.split('/').pop();
  return (!page || page === '') ? 'index.html' : page;
}


/**
 * 날짜 포맷 (YYYY-MM-DD)
 * @param {Date} [date=new Date()]
 * @returns {string}
 */
function formatDate(date = new Date()) {
  try {
    return date.toISOString().split('T')[0];
  } catch (err) {
    console.error('[app] 날짜 포맷 오류', err);
    return '';
  }
}

/**
 * 숫자 천 단위 구분자 포맷
 * @param {number} value
 * @returns {string}
 */
function formatNumber(value) {
  try {
    return new Intl.NumberFormat('ko-KR').format(value);
  } catch (err) {
    console.error('[app] 숫자 포맷 오류', err);
    return String(value);
  }
}

/* --------------------------------------------------------------------------
   사이드바 렌더링
   -------------------------------------------------------------------------- */

/**
 * 사이드바 HTML 생성 및 삽입
 * @param {string} [activeHref] - 현재 활성 메뉴 href
 */
function renderSidebar(activeHref) {
  const sidebar = qs('#sidebar');
  if (!sidebar) return;

  const currentPage = activeHref || getCurrentPage();

  const navItemsHTML = APP_CONFIG.NAV_ITEMS.map(item => {
    const isActive = currentPage === item.href || currentPage === item.href.replace('.html', '');
    const badgeHTML = item.badge
      ? `<span class="nav-badge">${item.badge}</span>`
      : '';

    return `
      <a href="${item.href}" class="sidebar-nav-item ${isActive ? 'active' : ''}" id="${item.id}">
        <span class="nav-icon">${ICONS[item.icon]}</span>
        ${item.label}
        ${badgeHTML}
      </a>
    `;
  }).join('');

  sidebar.innerHTML = `
    <div class="sidebar-brand">
      <a href="index.html" class="sidebar-brand-logo">
        <div class="sidebar-brand-icon">${ICONS.logo}</div>
        <div class="sidebar-brand-text">
          <span class="sidebar-brand-name">${APP_CONFIG.APP_NAME}</span>
          <span class="sidebar-brand-sub">${APP_CONFIG.APP_SUBTITLE}</span>
        </div>
      </a>
    </div>
    <nav class="sidebar-nav">
      <div class="sidebar-nav-label">메인 메뉴</div>
      ${navItemsHTML}
    </nav>
    <div class="sidebar-footer">
      <a href="workspace.html" class="btn-new-disclosure">
        ${ICONS.plus}
        새 공시 작성
      </a>
    </div>
  `;
}

/* --------------------------------------------------------------------------
   헤더 렌더링
   -------------------------------------------------------------------------- */

/**
 * 헤더 HTML 생성 및 삽입
 * @param {string} title - 헤더 제목
 * @param {string} [searchPlaceholder='공시 검색...'] - 검색창 placeholder
 */
function renderHeader(title, searchPlaceholder = '공시 검색...') {
  const header = qs('#page-header');
  if (!header) return;

  header.innerHTML = `
    <h1 class="page-header-title">${title}</h1>
    <div class="header-search">
      <span class="header-search-icon">${ICONS.search}</span>
      <input
        type="text"
        class="header-search-input"
        placeholder="${searchPlaceholder}"
        id="header-search-input"
        aria-label="공시 검색"
      />
    </div>
    <div class="header-actions">
      <button class="header-icon-btn" id="btn-notification" aria-label="알림" title="알림">
        ${ICONS.bell}
        <span class="header-notification-dot"></span>
      </button>
      <button class="header-icon-btn" id="btn-help" aria-label="도움말" title="도움말">
        ${ICONS.help}
      </button>
    </div>
  `;


  // 알림 버튼 클릭 이벤트
  const btnNotification = qs('#btn-notification', header);
  if (btnNotification) {
    btnNotification.addEventListener('click', () => {
      showToast('info', '알림', '새 공시 마감이 4시간 후입니다.');
    });
  }

  // 상단 헤더 공시 검색창 실시간 연동 (Live Filter & Enter 히스토리 이동)
  const searchInput = qs('#header-search-input', header);
  if (searchInput) {
    // URL에 기존 검색어가 있는 경우 복원
    const urlParams = new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get('q');
    if (initialQuery) {
      searchInput.value = initialQuery;
    }

    // 실시간 검색어 입력 시 전역 이벤트 발생 & 현재 페이지 테이블 필터링
    searchInput.addEventListener('input', (e) => {
      const query = (e.target.value || '').trim().toLowerCase();

      // 전역 CustomEvent 전파
      window.dispatchEvent(new CustomEvent('app:search', { detail: { query } }));

      // 현재 페이지의 테이블 행 실시간 필터링
      const tableRows = qsa('table tbody tr');
      if (tableRows && tableRows.length > 0) {
        tableRows.forEach(row => {
          const text = (row.textContent || '').toLowerCase();
          if (!query || text.includes(query)) {
            row.style.display = '';
          } else {
            row.style.display = 'none';
          }
        });
      }
    });

    // Enter 키 누르면 전체 히스토리 검색 페이지(history.html)로 이동
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
          showToast('info', '공시 검색', `'${query}' 검색 결과 페이지로 이동합니다.`);
          setTimeout(() => {
            window.location.href = `history.html?q=${encodeURIComponent(query)}`;
          }, 400);
        }
      }
    });
  }
}


/* --------------------------------------------------------------------------
   토스트 알림
   -------------------------------------------------------------------------- */

// 토스트 컨테이너 초기화
function initToastContainer() {
  if (qs('#toast-container')) return;
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'toast-container';
  document.body.appendChild(container);
}

/**
 * 토스트 알림 표시 (사용자가 닫기 버튼을 직접 누를 때만 사라집니다)
 * @param {'success'|'danger'|'warning'|'info'} type - 타입
 * @param {string} title - 제목
 * @param {string} message - 내용
 */
function showToast(type, title, message) {
  try {
    initToastContainer();
    const container = qs('#toast-container');
    if (!container) return;

    const ICON_MAP = {
      success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
      danger:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
      warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      info:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    };

    const COLOR_MAP = {
      success: 'var(--color-success)',
      danger:  'var(--color-danger)',
      warning: 'var(--color-warning)',
      info:    'var(--color-primary)',
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.position = 'relative';
    toast.style.paddingRight = '36px';

    toast.innerHTML = `
      <span class="toast-icon" style="color:${COLOR_MAP[type] || 'currentColor'}">${ICON_MAP[type] || ''}</span>
      <div style="flex:1">
        <div class="toast-title">${title}</div>
        <div class="toast-body">${message}</div>
      </div>
      <button type="button" class="toast-close-btn" aria-label="닫기" style="
        position: absolute;
        top: 12px;
        right: 10px;
      ">✕</button>
    `;

    // 닫기 버튼 클릭 이벤트 핸들러 (사용자가 수동으로 ✕ 누를 때만 닫힘)
    const closeBtn = toast.querySelector('.toast-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => {
          if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
      });
    }

    container.appendChild(toast);


  } catch (err) {
    console.error('[app] 토스트 표시 오류', err);
  }
}


/* --------------------------------------------------------------------------
   앱 초기화 (DOMContentLoaded 시 실행)
   -------------------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  try {
    initToastContainer();

    // 페이지 내 사이드바 및 헤더가 비어있을 경우 자동 전역 렌더링 보장
    const currentPage = getCurrentPage();
    const sidebarEl = qs('#sidebar');
    if (sidebarEl && (!sidebarEl.children || sidebarEl.children.length === 0)) {
      renderSidebar(currentPage);
      console.log('[app] 사이드바 자동 전역 렌더링 실행 완료');
    }

    const headerEl = qs('#page-header');
    if (headerEl && (!headerEl.children || headerEl.children.length === 0)) {
      renderHeader('공시 자동화 시스템');
      console.log('[app] 헤더 자동 전역 렌더링 실행 완료');
    }

    console.log(`[app] ${APP_CONFIG.APP_NAME} 초기화 완료 - 페이지: ${currentPage}`);
  } catch (err) {
    console.error('[app] 초기화 오류', err);
  }
});

/* --------------------------------------------------------------------------
   외부 공개 (전역 접근)
   -------------------------------------------------------------------------- */
window.DisclosureApp = {
  config: APP_CONFIG,
  icons: ICONS,
  utils: { qs, qsa, formatDate, formatNumber, getCurrentPage },
  ui: { renderSidebar, renderHeader, showToast },
};

// 스크립트 로드 즉시 전역 객체 할당
if (typeof window !== 'undefined') {
  window.DisclosureApp = window.DisclosureApp || {
    config: APP_CONFIG,
    icons: ICONS,
    utils: { qs, qsa, formatDate, formatNumber, getCurrentPage },
    ui: { renderSidebar, renderHeader, showToast },
  };
}

