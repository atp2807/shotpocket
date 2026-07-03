/* eslint-disable no-console */
// 애플리케이션 전역 로거. 컴포넌트/서비스는 console 대신 이 로거를 사용한다.
// debug/info 는 개발 환경에서만 출력, warn/error 는 항상 출력.

const IS_DEV = Boolean(import.meta.env && import.meta.env.DEV);

export const logger = {
  debug: (...args) => {
    if (IS_DEV) {
      console.log('[debug]', ...args);
    }
  },
  info: (...args) => {
    if (IS_DEV) {
      console.info('[info]', ...args);
    }
  },
  warn: (...args) => {
    console.warn('[warn]', ...args);
  },
  error: (...args) => {
    console.error('[error]', ...args);
  },
};
