// 로컬 개인화. 계정/서버 프로필이 없으므로 localStorage 만으로 관심사를 추정한다.
// - sp_engaged: 좋아요/다운로드한 짤의 링버퍼(최대 200). 피드 개인화(similar 믹스)의 씨앗.
// - sp_liked:   좋아요한 짤 id 집합. 재방문 시 하트 채움 상태 복원용.
import { logger } from './logger.js';

const ENGAGED_KEY = 'sp_engaged';
const LIKED_KEY = 'sp_liked';
const MAX_ENGAGED = 200;

function readJson(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : fallback;
  } catch (err) {
    logger.warn('localStorage 읽기 실패', key, err);
    return fallback;
  }
}

function writeJson(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (err) {
    logger.warn('localStorage 쓰기 실패', key, err);
  }
}

// 좋아요/다운로드 시 호출. 링버퍼(FIFO)로 최대 200개 유지.
export function recordEngagement(memeId) {
  if (!memeId) {
    return;
  }
  const list = readJson(ENGAGED_KEY, []).filter((e) => e && e.meme_id !== memeId);
  list.push({ meme_id: memeId, ts: Date.now() });
  const trimmed = list.slice(-MAX_ENGAGED);
  writeJson(ENGAGED_KEY, trimmed);
}

export function getEngagedIds() {
  return readJson(ENGAGED_KEY, [])
    .map((e) => e && e.meme_id)
    .filter(Boolean);
}

// 피드 개인화 씨앗: 최근 engaged 중 무작위 1개 id (없으면 null).
export function pickSeedMemeId() {
  const ids = getEngagedIds();
  if (ids.length === 0) {
    return null;
  }
  // 최근 30개에 가중치를 두어 무작위 선택
  const pool = ids.slice(-30);
  return pool[Math.floor(Math.random() * pool.length)];
}

export function markLiked(memeId) {
  if (!memeId) {
    return;
  }
  const set = new Set(readJson(LIKED_KEY, []));
  set.add(memeId);
  writeJson(LIKED_KEY, Array.from(set).slice(-MAX_ENGAGED));
}

export function isLiked(memeId) {
  if (!memeId) {
    return false;
  }
  return readJson(LIKED_KEY, []).includes(memeId);
}
