from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Float,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), default="user")
    avatar_url = Column(String(512), nullable=True)
    totp_secret = Column(String(64), nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(64), primary_key=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)


class APIToken(Base):
    __tablename__ = "api_tokens"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(128), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False)
    scopes = Column(Text, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class InvitationKey(Base):
    __tablename__ = "invitation_keys"
    id = Column(BigInteger, primary_key=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text)
    ip_address = Column(String(45))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(BigInteger, primary_key=True)
    agent_id = Column(String(64), nullable=False)
    src_ip = Column(String(45), nullable=False)
    method = Column(String(16), nullable=False)
    path = Column(String(255), nullable=False)
    status_code = Column(Integer, nullable=False)
    verdict = Column(String(16), nullable=False)  # allowed / blocked
    latency_ms = Column(Integer, nullable=False)

    # Новые поля для ML-анализа
    bot_probability = Column(Float, nullable=True)
    risk_level = Column(String(16), nullable=True)  # low / medium / high
    ml_model_used = Column(String(64), nullable=True)
    is_bot = Column(Boolean, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class Upload(Base):
    __tablename__ = "uploads"
    id = Column(String(64), primary_key=True)  # upload_id (UUID)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    total_size = Column(BigInteger, nullable=False)
    chunk_size = Column(Integer, default=10 * 1024 * 1024)  # 10 МБ
    total_chunks = Column(Integer, nullable=False)
    uploaded_chunks = Column(Integer, default=0)
    checksum = Column(String(64), nullable=False)  # SHA-256
    status = Column(
        String(16), default="in_progress"
    )  # in_progress / completed / failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Agent(Base):
    __tablename__ = "agents"
    id = Column(BigInteger, primary_key=True)
    agent_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(128), nullable=False)
    domain = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User", backref="agents")


class UserMLSettings(Base):
    __tablename__ = "user_ml_settings"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    ml_model = Column(String(64), default="isolation_forest")
    ml_threshold = Column(Float, default=0.65)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
