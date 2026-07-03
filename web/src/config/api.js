import { API_ROUTES } from '@shotpocket/shared';

export const API_CONFIG = {
  // 개발 환경에서는 vite proxy 를 타므로 기본값은 빈 문자열(상대 경로)
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '',
  TIMEOUT_MS: 10000,
};

// 컴포넌트/서비스가 config 한 곳에서 경로를 받도록 re-export
export { API_ROUTES };
