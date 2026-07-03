// ShotPocket 에러 코드 (단일 정본). 응답 형식: { error_code, message }.

export const ERROR_CODES = {
  COMMON_001: { code: 'COMMON_001', message: '잘못된 요청입니다.' },
  COMMON_002: { code: 'COMMON_002', message: '서버 오류가 발생했습니다.' },
  COMMON_003: { code: 'COMMON_003', message: '요청 한도를 초과했습니다.' },
  MEME_001: { code: 'MEME_001', message: '짤을 찾을 수 없습니다.' },
  SEARCH_001: { code: 'SEARCH_001', message: '검색어가 비어 있습니다.' },
  SEARCH_002: { code: 'SEARCH_002', message: '검색 처리에 실패했습니다.' },
  FEED_001: { code: 'FEED_001', message: '잘못된 커서입니다.' },
  ENGAGE_001: { code: 'ENGAGE_001', message: '중복 요청입니다.' },
  REPORT_001: { code: 'REPORT_001', message: '잘못된 신고 사유입니다.' },
  OPS_001: { code: 'OPS_001', message: '권한이 없습니다.' },
};
