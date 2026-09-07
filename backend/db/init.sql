-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'user',
    avatar_url VARCHAR(512),
    totp_secret VARCHAR(64),
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица сессий
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Таблица API токенов
CREATE TABLE IF NOT EXISTS api_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    token_hash VARCHAR(128) UNIQUE NOT NULL,
    scopes TEXT,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Таблица инвайт-ключей
CREATE TABLE IF NOT EXISTS invitation_keys (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(64) UNIQUE NOT NULL,
    created_by BIGINT NOT NULL REFERENCES users(id),
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица аудита
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Таблица логов запросов (КРИТИЧЕСКИ ВАЖНО для ML)
CREATE TABLE IF NOT EXISTS request_logs (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    src_ip VARCHAR(45) NOT NULL,
    method VARCHAR(16) NOT NULL,
    path VARCHAR(255) NOT NULL,
    status_code INTEGER NOT NULL,
    verdict VARCHAR(16) NOT NULL,
    latency_ms INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_user ON api_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_invite_key ON invitation_keys (key);
CREATE INDEX IF NOT EXISTS idx_request_logs_agent ON request_logs (agent_id);