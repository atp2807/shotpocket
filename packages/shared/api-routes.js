// ShotPocket API 경로 (단일 정본). 컴포넌트/서비스는 URL 하드코딩 대신 이 상수를 사용한다.

export const API_ROUTES = {
  MEMES: {
    DETAIL: (id) => `/api/memes/${id}`,
    SIMILAR: (id) => `/api/memes/${id}/similar`,
    LIKES: (id) => `/api/memes/${id}/likes`,
    DOWNLOADS: (id) => `/api/memes/${id}/downloads`,
  },
  SEARCH: {
    QUERY: '/api/search',
  },
  FEED: {
    LIST: '/api/feed',
  },
  REPORTS: {
    CREATE: '/api/reports',
  },
  OPS: {
    REPORTS: '/api/ops/reports',
    STATS: '/api/ops/stats',
  },
};
