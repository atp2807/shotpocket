-- ShotPocket 시간대별 인게이지 집계 (raw SQL 마이그레이션, alembic 미사용)
-- 2026-07-03 engage_hourly
-- 목적: view/like/download 를 (meme_id, hour_ts) 시간버킷으로 누적 집계.
--       피드 today(최근 24h)/rising(최근 2h 가속도) 섹션의 정렬 근거.
--       meme_stat(누적 카운터)와 별개 — 이쪽은 시간창 롤업용, 7일 지난 row 는 잡이 정리.

CREATE TABLE IF NOT EXISTS stat.engage_hourly (
    meme_id      UUID        NOT NULL REFERENCES meme.meme (id) ON DELETE CASCADE,
    hour_ts      TIMESTAMPTZ NOT NULL,          -- date_trunc('hour', now())
    view_cnt     INTEGER     NOT NULL DEFAULT 0,
    like_cnt     INTEGER     NOT NULL DEFAULT 0,
    download_cnt INTEGER     NOT NULL DEFAULT 0,
    PRIMARY KEY (meme_id, hour_ts)
);
-- hour_ts 단독 인덱스: 시간창 스캔(today/rising 집계) + 7일 경과 정리 잡용
CREATE INDEX IF NOT EXISTS ix_stat_engage_hourly_hour_ts ON stat.engage_hourly (hour_ts);
