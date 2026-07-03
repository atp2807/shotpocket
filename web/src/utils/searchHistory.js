// 최근 검색어 로컬 기록(최대 8개, 최신 우선). 서버/계정 없음.
import { logger } from './logger.js';

const KEY = 'sp_recent_searches';
const MAX = 8;

export function getRecentSearches() {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((s) => typeof s === 'string') : [];
  } catch (err) {
    logger.warn('최근 검색어 읽기 실패', err);
    return [];
  }
}

export function pushRecentSearch(term) {
  const q = (term || '').trim();
  if (!q) {
    return getRecentSearches();
  }
  const next = [q, ...getRecentSearches().filter((s) => s !== q)].slice(0, MAX);
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch (err) {
    logger.warn('최근 검색어 쓰기 실패', err);
  }
  return next;
}

export function clearRecentSearches() {
  try {
    window.localStorage.removeItem(KEY);
  } catch (err) {
    logger.warn('최근 검색어 삭제 실패', err);
  }
}
