-- 짤 태그 추가 (검색·브라우징·시리즈 모아보기 핵심 신호)
-- 규약: 같은 날짜 파일명 알파벳 정렬 함정(lr-333a4e1a 교훈) 방지 위해 시퀀스 번호(_1) 부여.
ALTER TABLE meme.analysis
    ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';

-- 태그 배열 검색(? 연산자/포함 매칭)용 GIN 인덱스
CREATE INDEX IF NOT EXISTS ix_meme_analysis_tags ON meme.analysis USING gin (tags);
