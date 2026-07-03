-- ShotPocket 초기 스키마 (raw SQL 마이그레이션, alembic 미사용)
-- 2026-07-03 init
-- 규약: 스키마 4개(meme/ingest/stat/ops, public 금지), 테이블 단수 snake_case,
--       PK UUID id DEFAULT gen_random_uuid(), 접미사 _cd/_ts/_cnt/_url/_hash/_key,
--       created_ts/updated_ts. TIMESTAMPTZ.

-- ==== 확장 ====
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector (임베딩 유사도)
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

-- ==== 스키마 ====
CREATE SCHEMA IF NOT EXISTS meme;
CREATE SCHEMA IF NOT EXISTS ingest;
CREATE SCHEMA IF NOT EXISTS stat;
CREATE SCHEMA IF NOT EXISTS ops;

-- ==== meme 스키마 ====
CREATE TABLE IF NOT EXISTS meme.meme (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phash         VARCHAR(64),
    media_type_cd VARCHAR(16)  NOT NULL DEFAULT 'STILL',  -- STILL | LOOP
    duration_ms   INTEGER,
    width         INTEGER,
    height        INTEGER,
    r2_orig_key   VARCHAR(512),
    r2_mp4_key    VARCHAR(512),
    r2_thumb_key  VARCHAR(512),
    origin_url    TEXT,
    source_cd     VARCHAR(32),
    status_cd     VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    created_ts    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_ts    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_meme_meme_phash     ON meme.meme (phash);
CREATE INDEX IF NOT EXISTS ix_meme_meme_status_cd ON meme.meme (status_cd);

CREATE TABLE IF NOT EXISTS meme.analysis (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meme_id        UUID NOT NULL REFERENCES meme.meme (id) ON DELETE CASCADE,
    caption        TEXT,
    situation      TEXT,
    emotion_cd     VARCHAR(32),
    ocr_text       TEXT,
    usage_context  TEXT,
    character_name VARCHAR(128),
    meme_name      VARCHAR(128),
    lang_cd        VARCHAR(8),
    nsfw_score     NUMERIC(5,4),
    confidence     NUMERIC(5,4),
    model_cd       VARCHAR(64),
    created_ts     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_meme_analysis_meme_id ON meme.analysis (meme_id);

CREATE TABLE IF NOT EXISTS meme.embedding (
    meme_id   UUID PRIMARY KEY REFERENCES meme.meme (id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL   -- bge-m3 (1024차원)
);
-- HNSW 코사인 인덱스 (의미 유사도 검색)
CREATE INDEX IF NOT EXISTS ix_meme_embedding_hnsw
    ON meme.embedding USING hnsw (embedding vector_cosine_ops);

-- ==== ingest 스키마 ====
CREATE TABLE IF NOT EXISTS ingest.source (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(128) NOT NULL,
    base_url       TEXT,
    source_type_cd VARCHAR(32) NOT NULL DEFAULT 'WEB',
    priority       INTEGER NOT NULL DEFAULT 100,
    enabled_yn     BOOLEAN NOT NULL DEFAULT TRUE,
    created_ts     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingest.raw_item (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id        UUID NOT NULL REFERENCES ingest.source (id) ON DELETE CASCADE,
    origin_url       TEXT,
    phash            VARCHAR(64),
    status_cd        VARCHAR(16) NOT NULL DEFAULT 'FETCHED',
    reject_reason_cd VARCHAR(32),
    payload          JSONB,
    created_ts       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_ts       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ingest_raw_item_status_cd ON ingest.raw_item (status_cd);
CREATE INDEX IF NOT EXISTS ix_ingest_raw_item_phash     ON ingest.raw_item (phash);
CREATE INDEX IF NOT EXISTS ix_ingest_raw_item_source_id ON ingest.raw_item (source_id);

-- ==== stat 스키마 ====
CREATE TABLE IF NOT EXISTS stat.meme_stat (
    meme_id      UUID PRIMARY KEY REFERENCES meme.meme (id) ON DELETE CASCADE,
    view_cnt     INTEGER NOT NULL DEFAULT 0,
    like_cnt     INTEGER NOT NULL DEFAULT 0,
    download_cnt INTEGER NOT NULL DEFAULT 0,
    rank_score   NUMERIC(12,4) NOT NULL DEFAULT 0,
    updated_ts   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stat_meme_stat_rank_score ON stat.meme_stat (rank_score DESC);

CREATE TABLE IF NOT EXISTS stat.query_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL,
    result_cnt INTEGER NOT NULL DEFAULT 0,
    failed_yn  BOOLEAN NOT NULL DEFAULT FALSE,
    ip_hash    VARCHAR(64),                 -- PII 비저장: IP 는 sha256 해시만
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==== ops 스키마 ====
CREATE TABLE IF NOT EXISTS ops.report (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meme_id    UUID NOT NULL REFERENCES meme.meme (id) ON DELETE CASCADE,
    reason_cd  VARCHAR(32) NOT NULL,          -- COPYRIGHT|PORTRAIT_RIGHT|NSFW|HATE|SPAM|ETC
    status_cd  VARCHAR(16) NOT NULL DEFAULT 'AUTO_HIDDEN',  -- 신고=자동 비공개. AUTO_HIDDEN→RESTORED|REMOVED (PENDING 없음)
    contact    VARCHAR(256),
    detail     TEXT,
    ip_hash    VARCHAR(64),                 -- PII 비저장
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ops_report_meme_id   ON ops.report (meme_id);
CREATE INDEX IF NOT EXISTS ix_ops_report_status_cd ON ops.report (status_cd);

-- ==== 권한(GRANT) 스켈레톤 ====
-- 운영 배포 시 애플리케이션 롤을 만들어 최소권한만 부여한다. 예시:
--   CREATE ROLE shotpocket_app LOGIN PASSWORD '***';
--   GRANT USAGE ON SCHEMA meme, ingest, stat, ops TO shotpocket_app;
--   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA meme, ingest, stat, ops TO shotpocket_app;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA meme, ingest, stat, ops
--       GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO shotpocket_app;
-- public 스키마는 사용하지 않는다(REVOKE ALL ON SCHEMA public FROM PUBLIC 권장).
