// 컨텍스트 없는 토스트 유틸. DOM 포탈에 직접 append 하고 자동 소멸한다.
// 사용: import { showToast } from '.../Toast.js'; showToast('저장됨', 'success');
import './Toast.css';

const PORTAL_ID = 'sp-toast-portal';
const DEFAULT_DURATION = 2600;

function getPortal() {
  if (typeof document === 'undefined') {
    return null;
  }
  let portal = document.getElementById(PORTAL_ID);
  if (!portal) {
    portal = document.createElement('div');
    portal.id = PORTAL_ID;
    portal.className = 'toast-portal';
    document.body.appendChild(portal);
  }
  return portal;
}

// variant: 'default' | 'success' | 'danger'
export function showToast(message, variant = 'default', duration = DEFAULT_DURATION) {
  const portal = getPortal();
  if (!portal || !message) {
    return;
  }

  const el = document.createElement('div');
  el.className =
    variant === 'default' ? 'toast toast--stack' : `toast toast--stack toast--${variant}`;
  el.setAttribute('role', 'status');
  el.textContent = message;
  portal.appendChild(el);

  // 다음 프레임에 enter 클래스 → 트랜지션 발동
  requestAnimationFrame(() => {
    el.classList.add('toast--in');
  });

  const remove = () => {
    el.classList.remove('toast--in');
    el.addEventListener(
      'transitionend',
      () => {
        el.remove();
        if (portal.childElementCount === 0) {
          portal.remove();
        }
      },
      { once: true },
    );
  };

  setTimeout(remove, duration);
}
