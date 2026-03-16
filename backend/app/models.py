"""
第二人生平台 - 数据库模型
完整实现PRD中定义的所有实体关系
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Enum, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import hashlib
import uuid
import secrets

Base = declarative_base()

# ==================== 枚举类型 ====================

class UserRole(enum.Enum):
    ADMIN = "admin"
    PUBLISHER = "publisher" 
    ACCEPTOR = "acceptor"
    BOTH = "both"

class TaskStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

class VisibilityLevel(enum.Enum):
    L1_PUBLIC = "l1"          # 公开摘要
    L2_QUALIFIED = "l2"       # 资格验证后可见
    L3_INVITATION = "l3"      # 邀请制
    L4_ANONYMOUS = "l4"       # 完全匿名

class EscrowStatus(enum.Enum):
    PENDING = "pending"
    HELD = "held"
    RELEASED = "released"
    REFUNDED = "refunded"

class MessageType(enum.Enum):
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"

# ==================== 用户模型 ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    
    # 密码安全
    password_hash = Column(String(255), nullable=False)
    
    # 用户角色与状态
    role = Column(Enum(UserRole), default=UserRole.BOTH)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # 信用体系
    credit_score = Column(Float, default=100.0)
    credit_level = Column(Integer, default=1)
    
    # 匿名标识系统
    anonymous_id = Column(String(32), unique=True, 
                         default=lambda: hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16])
    
    # 保证金
    deposit_amount = Column(Float, default=0.0)
    deposit_currency = Column(String(10), default="CNY")
    deposit_status = Column(Boolean, default=False)
    
    # 用户资料
    real_name = Column(String(100), nullable=True)
    id_verified = Column(Boolean, default=False)
    professional_title = Column(String(200), nullable=True)
    industry = Column(String(100), nullable=True)
    skills = Column(JSON, default=list)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # 关系
    published_tasks = relationship("Task", foreign_keys="Task.publisher_id", back_populates="publisher")
    accepted_tasks = relationship("Task", foreign_keys="Task.acceptor_id", back_populates="acceptor")
    ratings_given = relationship("Rating", foreign_keys="Rating.rater_id", back_populates="rater")
    ratings_received = relationship("Rating", foreign_keys="Rating.ratee_id", back_populates="ratee")
    chat_messages = relationship("ChatMessage", back_populates="sender")

# ==================== 任务模型 ====================

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_token = Column(String(32), unique=True, 
                       default=lambda: "TASK_" + secrets.token_hex(4).upper())
    
    # 参与方
    publisher_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    publisher = relationship("User", foreign_keys=[publisher_id], back_populates="published_tasks")
    acceptor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    acceptor = relationship("User", foreign_keys=[acceptor_id], back_populates="accepted_tasks")
    
    # 任务信息
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    tags = Column(JSON, default=list)
    
    # 可见性等级
    visibility_level = Column(Enum(VisibilityLevel), default=VisibilityLevel.L1_PUBLIC)
    status = Column(Enum(TaskStatus), default=TaskStatus.DRAFT)
    
    # 预算
    budget_min = Column(Float, nullable=False)
    budget_max = Column(Float, nullable=False)
    currency = Column(String(10), default="CNY")
    
    # 内容存储 (加密)
    description_encrypted = Column(Text, nullable=True)
    requirements_encrypted = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # 公开可见的摘要
    
    # 任务参数
    location = Column(String(200), nullable=True)
    deadline = Column(DateTime, nullable=True)
    min_credit_level = Column(Integer, default=1)
    required_skills = Column(JSON, default=list)
    
    # 邀请制
    is_invitation_only = Column(Boolean, default=False)
    invited_users = Column(JSON, default=list)
    
    # 匿名设置
    publisher_anonymous = Column(Boolean, default=False)
    acceptor_anonymous = Column(Boolean, default=False)
    publisher_token = Column(String(32), nullable=True)  # @SL_Pub_xxxxx
    acceptor_token = Column(String(32), nullable=True)   # @SL_Acc_xxxxx
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    escrow = relationship("Escrow", uselist=False, back_populates="task")
    chat_messages = relationship("ChatMessage", back_populates="task")
    ratings = relationship("Rating", back_populates="task")
    
    # 索引
    __table_args__ = (
        Index('idx_task_status_visibility', 'status', 'visibility_level'),
        Index('idx_task_category', 'category'),
    )

# ==================== 资金托管模型 ====================

class Escrow(Base):
    __tablename__ = "escrows"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    escrow_token = Column(String(32), unique=True,
                         default=lambda: "ESC_" + secrets.token_hex(4).upper())
    
    task_id = Column(String(36), ForeignKey("tasks.id"), unique=True, nullable=False)
    task = relationship("Task", back_populates="escrow")
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="CNY")
    status = Column(Enum(EscrowStatus), default=EscrowStatus.PENDING)
    
    # 支付信息
    payment_method = Column(String(50), nullable=True)
    payment_tx_id = Column(String(255), nullable=True)
    
    # 区块链信息
    blockchain_tx_hash = Column(String(100), nullable=True)
    smart_contract_address = Column(String(100), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)

# ==================== 即时通讯模型 ====================

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="chat_messages")
    
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    sender = relationship("User", back_populates="chat_messages")
    
    # 消息内容
    content_encrypted = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # 完整性校验
    
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    
    # 隐私保护
    has_sensitive_info = Column(Boolean, default=False)
    masked_content = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_chat_task_time', 'task_id', 'created_at'),
    )

# ==================== 信用评级模型 ====================

class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="ratings")
    
    rater_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    rater = relationship("User", foreign_keys=[rater_id], back_populates="ratings_given")
    
    ratee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    ratee = relationship("User", foreign_keys=[ratee_id], back_populates="ratings_received")
    
    # 评分维度 (1-5分)
    professionalism = Column(Integer, default=5)
    communication = Column(Integer, default=5)
    quality = Column(Integer, default=5)
    privacy_respect = Column(Integer, default=5)
    overall_score = Column(Float, nullable=False)
    
    comment = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=False)  # 互评后才可见
    
    created_at = Column(DateTime, default=datetime.utcnow)

# ==================== 审计日志模型 ====================

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(36), nullable=True)
    details = Column(JSON, default=dict)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_created', 'created_at'),
    )

# ==================== 数据库初始化 ====================

def init_db(database_url: str = "sqlite:///./secondlife.db"):
    """初始化数据库"""
    engine = create_engine(database_url, echo=False, connect_args={"check_same_thread": False} if "sqlite" in database_url else {})
    Base.metadata.create_all(engine)
    return engine

def get_session_maker(engine):
    """获取会话工厂"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
