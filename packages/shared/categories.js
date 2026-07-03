// ShotPocket 코드값 상수 (단일 정본). 문자열 리터럴 비교 대신 이 상수를 import 한다.

export const MEDIA_TYPE = {
  STILL: 'STILL',
  LOOP: 'LOOP',
};

export const MEME_STATUS = {
  PENDING: 'PENDING', // R2 업로드 전 (orphan 방지)
  ACTIVE: 'ACTIVE',
  HIDDEN: 'HIDDEN',
  REMOVED: 'REMOVED',
};

export const RAW_ITEM_STATUS = {
  FETCHED: 'FETCHED',
  DEDUPED: 'DEDUPED',
  ANALYZED: 'ANALYZED',
  PUBLISHED: 'PUBLISHED',
  REJECTED: 'REJECTED',
};

export const EMOTION = {
  JOY: 'JOY',
  SADNESS: 'SADNESS',
  ANGER: 'ANGER',
  TIRED: 'TIRED',
  AWKWARD: 'AWKWARD',
  PANIC: 'PANIC',
  PROUD: 'PROUD',
  LOVE: 'LOVE',
  DISGUST: 'DISGUST',
  SURPRISE: 'SURPRISE',
};

export const EMOTION_LABEL = {
  JOY: '기쁨',
  SADNESS: '슬픔',
  ANGER: '분노',
  TIRED: '피곤',
  AWKWARD: '어색',
  PANIC: '당황',
  PROUD: '뿌듯',
  LOVE: '애정',
  DISGUST: '현타',
  SURPRISE: '놀람',
};

export const SITUATION = {
  WORK: 'WORK',
  SCHOOL: 'SCHOOL',
  FRIEND: 'FRIEND',
  LOVE: 'LOVE',
  GAME: 'GAME',
  FOOD: 'FOOD',
  MONEY: 'MONEY',
  EXERCISE: 'EXERCISE',
  WEATHER: 'WEATHER',
  ETC: 'ETC',
};

export const SITUATION_LABEL = {
  WORK: '회사',
  SCHOOL: '학교',
  FRIEND: '친구',
  LOVE: '연애',
  GAME: '게임',
  FOOD: '음식',
  MONEY: '돈',
  EXERCISE: '운동',
  WEATHER: '날씨',
  ETC: '기타',
};

export const REPORT_REASON = {
  COPYRIGHT: 'COPYRIGHT',
  PORTRAIT_RIGHT: 'PORTRAIT_RIGHT',
  NSFW: 'NSFW',
  HATE: 'HATE',
  SPAM: 'SPAM',
  ETC: 'ETC',
};

export const REPORT_STATUS = {
  AUTO_HIDDEN: 'AUTO_HIDDEN', // 신고 접수 = 즉시 자동 숨김 (무인 원칙)
  RESTORED: 'RESTORED',
  REMOVED: 'REMOVED',
};
