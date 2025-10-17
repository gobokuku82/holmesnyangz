-- ============================================================================
-- Complete Database Rebuild Migration
-- ============================================================================
-- 생성일: 2025-10-17
-- 목적: 전체 테이블 DROP 후 재생성
-- 주의: 모든 데이터가 삭제됩니다!
-- ============================================================================

-- ============================================================================
-- STEP 1: DROP ALL TABLES (역순으로 삭제 - FK 제약 고려)
-- ============================================================================

-- 1-1. Checkpoint 테이블 (FK 없음)
DROP TABLE IF EXISTS checkpoint_migrations CASCADE;
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
DROP TABLE IF EXISTS checkpoints CASCADE;

-- 1-2. Chat 테이블
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;

-- 1-3. 부동산 관련 테이블
DROP TABLE IF EXISTS trust_scores CASCADE;
DROP TABLE IF EXISTS nearby_facilities CASCADE;
DROP TABLE IF EXISTS real_estate_agents CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS real_estates CASCADE;
DROP TABLE IF EXISTS regions CASCADE;

-- 1-4. 사용자 관련 테이블
DROP TABLE IF EXISTS user_favorites CASCADE;
DROP TABLE IF EXISTS social_auths CASCADE;
DROP TABLE IF EXISTS local_auths CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1-5. ENUM 타입 삭제
DROP TYPE IF EXISTS usertype CASCADE;
DROP TYPE IF EXISTS gender CASCADE;
DROP TYPE IF EXISTS socialprovider CASCADE;
DROP TYPE IF EXISTS propertytype CASCADE;
DROP TYPE IF EXISTS transactiontype CASCADE;

-- ============================================================================
-- STEP 2: CREATE ENUM TYPES
-- ============================================================================

-- 사용자 타입
CREATE TYPE usertype AS ENUM ('admin', 'user', 'agent');

-- 성별
CREATE TYPE gender AS ENUM ('male', 'female', 'other');

-- 소셜 로그인 제공자
CREATE TYPE socialprovider AS ENUM ('google', 'kakao', 'naver', 'apple');

-- 부동산 종류
CREATE TYPE propertytype AS ENUM ('apartment', 'officetel', 'villa', 'single_house', 'commercial');

-- 거래 유형
CREATE TYPE transactiontype AS ENUM ('sale', 'jeonse', 'monthly_rent', 'short_term_rent');

-- ============================================================================
-- STEP 3: CREATE TABLES - 인증 & 사용자 (5 tables)
-- ============================================================================

-- 3-1. users (통합 사용자 테이블)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL UNIQUE,
    type usertype NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
COMMENT ON TABLE users IS '사용자 기본 정보 (인증 통합 테이블)';
COMMENT ON COLUMN users.email IS '이메일';
COMMENT ON COLUMN users.type IS '유저 타입';
COMMENT ON COLUMN users.is_active IS '계정 활성화 여부';

-- 3-2. user_profiles (사용자 프로필)
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    nickname VARCHAR(20) NOT NULL UNIQUE,
    bio TEXT,
    gender gender NOT NULL,
    birth_date VARCHAR(8) NOT NULL,
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE user_profiles IS '사용자 프로필 정보';

-- 3-3. local_auths (로컬 인증)
CREATE TABLE local_auths (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE local_auths IS '로컬 인증 (아이디/비밀번호)';

-- 3-4. social_auths (소셜 인증)
CREATE TABLE social_auths (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider socialprovider NOT NULL,
    provider_user_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE UNIQUE INDEX idx_provider_user ON social_auths(provider, provider_user_id);
COMMENT ON TABLE social_auths IS '소셜 인증 (카카오, 네이버, 구글, 애플)';

-- 3-5. user_favorites (사용자 찜 목록) - 나중에 FK 추가
CREATE TABLE user_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    real_estate_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- FK는 real_estates 테이블 생성 후 추가
COMMENT ON TABLE user_favorites IS '사용자 찜 목록';

-- ============================================================================
-- STEP 4: CREATE TABLES - 부동산 데이터 (6 tables)
-- ============================================================================

-- 4-1. regions (지역 정보)
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_regions_code ON regions(code);
COMMENT ON TABLE regions IS '지역 정보 (법정동 기준)';

-- 4-2. real_estates (부동산 매물)
CREATE TABLE real_estates (
    id SERIAL PRIMARY KEY,
    property_type propertytype NOT NULL,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    region_id INTEGER NOT NULL REFERENCES regions(id),
    address VARCHAR(255) NOT NULL,
    address_detail VARCHAR(255),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    total_households INTEGER,
    total_buildings INTEGER,
    completion_date VARCHAR(6),
    min_exclusive_area FLOAT,
    max_exclusive_area FLOAT,
    representative_area FLOAT,
    floor_area_ratio FLOAT,
    exclusive_area FLOAT,
    supply_area FLOAT,
    exclusive_area_pyeong FLOAT,
    supply_area_pyeong FLOAT,
    direction VARCHAR(20),
    floor_info VARCHAR(50),
    building_description TEXT,
    tag_list VARCHAR[],
    deal_count INTEGER,
    lease_count INTEGER,
    rent_count INTEGER,
    short_term_rent_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_real_estates_code ON real_estates(code);
COMMENT ON TABLE real_estates IS '부동산 매물 정보';

-- 4-3. transactions (거래 정보)
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER NOT NULL REFERENCES real_estates(id) ON DELETE CASCADE,
    region_id INTEGER NOT NULL REFERENCES regions(id),
    transaction_type transactiontype,
    transaction_date TIMESTAMP WITH TIME ZONE,
    sale_price INTEGER,
    deposit INTEGER,
    monthly_rent INTEGER,
    min_sale_price INTEGER,
    max_sale_price INTEGER,
    min_deposit INTEGER,
    max_deposit INTEGER,
    min_monthly_rent INTEGER,
    max_monthly_rent INTEGER,
    article_no VARCHAR(50) UNIQUE,
    article_confirm_ymd VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_transactions_article_no ON transactions(article_no);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_estate_date ON transactions(real_estate_id, transaction_date);
CREATE INDEX idx_transactions_date_type ON transactions(transaction_date, transaction_type);
COMMENT ON TABLE transactions IS '거래 정보 (매매, 전세, 월세)';

-- 4-4. real_estate_agents (중개사 정보)
CREATE TABLE real_estate_agents (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER NOT NULL REFERENCES real_estates(id) ON DELETE CASCADE,
    name VARCHAR(100),
    address VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE real_estate_agents IS '부동산 중개사 정보';

-- 4-5. nearby_facilities (주변 시설)
CREATE TABLE nearby_facilities (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER NOT NULL REFERENCES real_estates(id) ON DELETE CASCADE,
    facility_type VARCHAR(50),
    name VARCHAR(100),
    distance INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE nearby_facilities IS '주변 시설 정보';

-- 4-6. trust_scores (신뢰도 점수)
CREATE TABLE trust_scores (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER NOT NULL UNIQUE REFERENCES real_estates(id) ON DELETE CASCADE,
    score DECIMAL(3,2),
    data_quality INTEGER,
    transaction_activity INTEGER,
    price_stability INTEGER,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE trust_scores IS '부동산 신뢰도 점수';

-- user_favorites FK 추가 (이제 real_estates 존재)
ALTER TABLE user_favorites
ADD CONSTRAINT fk_user_favorites_real_estate
FOREIGN KEY (real_estate_id) REFERENCES real_estates(id) ON DELETE CASCADE;

CREATE UNIQUE INDEX idx_user_real_estate ON user_favorites(user_id, real_estate_id);

-- ============================================================================
-- STEP 5: CREATE TABLES - 채팅 & 세션 (2 tables)
-- ============================================================================

-- 5-1. chat_sessions (채팅 세션)
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at);

COMMENT ON TABLE chat_sessions IS '채팅 세션 (대화 스레드)';
COMMENT ON COLUMN chat_sessions.session_id IS 'Session ID (WebSocket 연결 식별자)';
COMMENT ON COLUMN chat_sessions.updated_at IS '세션 마지막 업데이트 (트리거 자동 갱신)';

-- 5-2. chat_messages (채팅 메시지)
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    structured_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_session_date ON chat_messages(session_id, created_at);

COMMENT ON TABLE chat_messages IS '채팅 메시지 히스토리';
COMMENT ON COLUMN chat_messages.role IS '메시지 역할: user | assistant | system';

-- ============================================================================
-- STEP 6: CREATE TABLES - LangGraph Checkpoint (4 tables)
-- ============================================================================

-- 6-1. checkpoints (LangGraph 상태 스냅샷)
CREATE TABLE checkpoints (
    session_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (session_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX idx_checkpoints_session ON checkpoints(session_id);

COMMENT ON TABLE checkpoints IS 'LangGraph 상태 스냅샷 (일시정지/재개용)';

-- 6-2. checkpoint_blobs (LangGraph 바이너리 데이터)
CREATE TABLE checkpoint_blobs (
    session_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (session_id, checkpoint_ns, channel, version)
);

COMMENT ON TABLE checkpoint_blobs IS 'LangGraph 바이너리 데이터 저장소';

-- 6-3. checkpoint_writes (LangGraph 증분 업데이트)
CREATE TABLE checkpoint_writes (
    session_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (session_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE INDEX idx_checkpoint_writes_session ON checkpoint_writes(session_id);

COMMENT ON TABLE checkpoint_writes IS 'LangGraph 증분 상태 업데이트';

-- 6-4. checkpoint_migrations (LangGraph 스키마 버전)
CREATE TABLE checkpoint_migrations (
    v INTEGER PRIMARY KEY
);

COMMENT ON TABLE checkpoint_migrations IS 'LangGraph 스키마 버전 추적';

-- LangGraph 마이그레이션 버전 초기화
INSERT INTO checkpoint_migrations (v) VALUES (1);

-- ============================================================================
-- STEP 7: CREATE TRIGGERS
-- ============================================================================

-- chat_sessions의 updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions
    SET updated_at = NOW()
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_chat_session_timestamp
AFTER INSERT ON chat_messages
FOR EACH ROW
EXECUTE FUNCTION update_chat_session_timestamp();

-- ============================================================================
-- STEP 8: INSERT DEFAULT DATA
-- ============================================================================

-- 기본 사용자 (user_id = 1)
INSERT INTO users (id, email, type, is_active)
VALUES (1, 'default@holmesnyangz.com', 'user', TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- 테이블 목록 확인
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
