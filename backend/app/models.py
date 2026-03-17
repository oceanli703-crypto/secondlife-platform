"""
第二人生平台 V2.0 - 数据库模型
对标猎聘，7步流程状态机，尊贵感设计
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

class IdentityType(enum.Enum):
    INDIVIDUAL = "individual"      # 个人
    COMPANY = "company"            # 公司

class KYCStatus(enum.Enum):
    UNVERIFIED = "unverified"      # 未认证
    PENDING = "pending"            # 审核中
    VERIFIED = "verified"          # 已认证
    REJECTED = "rejected"          # 认证失败

class TaskStepStatus(enum.Enum):
    """7步流程状态机"""
    STEP_1_PUBLISH = 1             # 发布
    STEP_2_VERIFY = 2              # 审核
    STEP_3_APPLY = 3               # 接单
    STEP_4_CONTRACT = 4            # 签约
    STEP_5_SUBMIT = 5              # 交付
    STEP_6_ACCEPT = 6              # 验收
    STEP_7_SETTLE = 7              # 结算

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
    L1_PUBLIC = "l1"          # 公开
    L2_ELITE = "l2"           # 精英可见
    L3_NDA = "l3"             # NDA后可见
    L4_SECRET = "l4"          # 完全保密

class PrivacyLevel(enum.Enum):
    """隐私等级 (0-2)"""
    PUBLIC = 0                # 公开
    ELITE_ONLY = 1            # 精英可见
    NDA_REQUIRED = 2          # NDA后可见

class EscrowStatus(enum.Enum):
    """资金托管状态 - 平台不碰资金，由银行/支付机构托管"""
    NOT_CREATED = "not_created"       # 未创建托管
    PENDING_PAYMENT = "pending_payment"  # 等待发布方付款到托管账户
    HELD_BY_BANK = "held_by_bank"     # 资金已在银行/支付机构托管
    RELEASED = "released"             # 已释放给接单方
    REFUNDED = "refunded"             # 已退还给发布方
    FROZEN = "frozen"                 # 纠纷冻结中

class DisputeStatus(enum.Enum):
    """纠纷处理状态"""
    OPEN = "open"                     # 已开启
    UNDER_REVIEW = "under_review"     # 人工审核中
    RESOLVED = "resolved"             # 已解决
    CLOSED = "closed"                 # 已关闭

class DisputeResolution(enum.Enum):
    """纠纷解决方式"""
    RELEASE_TO_ACCEPTOR = "release_to_acceptor"   # 资金释放给接单方
    REFUND_TO_PUBLISHER = "refund_to_publisher"   # 资金退还给发布方
    SPLIT = "split"                                 # 部分释放部分退还
    PENDING = "pending"                             # 待决定

class MessageType(enum.Enum):
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"

class ContractStatus(enum.Enum):
    """合同状态"""
    DRAFT = "draft"
    PENDING_PUBLISHER = "pending_publisher"    # 等待发布方签署
    PENDING_ACCEPTOR = "pending_acceptor"      # 等待接单方签署
    SIGNED = "signed"                          # 双方已签署
    EXPIRED = "expired"                        # 已过期

# ==================== 用户模型 (对标猎聘) ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    
    # 身份类型 (个人/公司)
    identity_type = Column(Enum(IdentityType), default=IdentityType.INDIVIDUAL)
    
    # 密码安全
    password_hash = Column(String(255), nullable=False)
    
    # 用户角色与状态
    role = Column(Enum(UserRole), default=UserRole.BOTH)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # 信用体系 (1-9级，对标猎聘)
    credit_score = Column(Float, default=100.0)
    credit_level = Column(Integer, default=1)              # 1-9级
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.UNVERIFIED)  # 实名状态
    
    # 匿名标识系统
    anonymous_id = Column(String(32), unique=True, 
                         default=lambda: hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16])
    
    # 隐私模式 (对标猎聘)
    is_anonymous_profile = Column(Boolean, default=False)   # 匿名展示简历
    reveal_after_approval = Column(Boolean, default=True)   # 获得同意后展示真实信息
    
    # 保证金
    deposit_amount = Column(Float, default=0.0)
    deposit_currency = Column(String(10), default="CNY")
    deposit_status = Column(Boolean, default=False)
    
    # 用户资料 (猎聘式简历)
    real_name = Column(String(100), nullable=True)
    id_verified = Column(Boolean, default=False)
    professional_title = Column(String(200), nullable=True)   # 职业头衔
    industry = Column(String(100), nullable=True)              # 行业
    skills = Column(JSON, default=list)                        # 技能树图谱
    
    # 大厂经历 (JSON格式存储多个经历)
    work_experience = Column(JSON, default=list)              # [{company, position, duration, highlights}]
    core_cases = Column(JSON, default=list)                   # 核心咨询案例
    education = Column(JSON, default=list)                    # 教育背景
    certifications = Column(JSON, default=list)               # 专业认证
    
    # 数字名片
    digital_card = Column(JSON, default=dict)                 # {title, summary, highlights}
    
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
    contracts = relationship("Contract", foreign_keys="Contract.publisher_id", back_populates="publisher")
    signed_contracts = relationship("Contract", foreign_keys="Contract.acceptor_id", back_populates="acceptor")

# ==================== 任务模型 (7步流程) ====================

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
    
    # 可见性与隐私
    visibility_level = Column(Enum(VisibilityLevel), default=VisibilityLevel.L1_PUBLIC)
    privacy_level = Column(Integer, default=0)                # 0:公开, 1:精英可见, 2:NDA后可见
    
    # 7步流程状态
    step_status = Column(Integer, default=1)                  # 1-7阶段
    status = Column(Enum(TaskStatus), default=TaskStatus.DRAFT)
    
    # 审核信息
    ai_reviewed = Column(Boolean, default=False)              # AI自动审核
    ai_review_result = Column(JSON, default=dict)             # AI审核结果
    admin_reviewed = Column(Boolean, default=False)           # 管理员审核
    admin_notes = Column(Text, nullable=True)                 # 管理员备注
    
    # 预算
    budget_min = Column(Float, nullable=False)
    budget_max = Column(Float, nullable=False)
    currency = Column(String(10), default="CNY")
    
    # 内容存储 (加密)
    description_encrypted = Column(Text, nullable=True)
    requirements_encrypted = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)                     # 公开可见的摘要
    
    # 任务参数
    location = Column(String(200), nullable=True)
    deadline = Column(DateTime, nullable=True)
    min_credit_level = Column(Integer, default=1)
    required_skills = Column(JSON, default=list)
    
    # NDA要求
    nda_required = Column(Boolean, default=False)             # 是否需要NDA
    nda_signed_by_acceptor = Column(Boolean, default=False)   # 接单方是否签署
    nda_content_hash = Column(String(64), nullable=True)      # NDA内容哈希
    
    # 邀请制
    is_invitation_only = Column(Boolean, default=False)
    invited_users = Column(JSON, default=list)
    
    # 匿名设置
    publisher_anonymous = Column(Boolean, default=False)
    acceptor_anonymous = Column(Boolean, default=False)
    publisher_token = Column(String(32), nullable=True)       # @SL_Pub_xxxxx
    acceptor_token = Column(String(32), nullable=True)        # @SL_Acc_xxxxx
    
    # 交付证据链
    deliverables = Column(JSON, default=list)                 # [{type, url, hash, timestamp}]
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)             # 审核通过时间
    accepted_at = Column(DateTime, nullable=True)
    contracted_at = Column(DateTime, nullable=True)           # 合同签署时间
    submitted_at = Column(DateTime, nullable=True)            # 交付时间
    accepted_by_publisher_at = Column(DateTime, nullable=True) # 验收时间
    settled_at = Column(DateTime, nullable=True)              # 结算时间
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    escrow = relationship("Escrow", uselist=False, back_populates="task")
    chat_messages = relationship("ChatMessage", back_populates="task")
    ratings = relationship("Rating", back_populates="task")
    contract = relationship("Contract", uselist=False, back_populates="task")
    
    # 索引
    __table_args__ = (
        Index('idx_task_status_visibility', 'status', 'visibility_level'),
        Index('idx_task_step_status', 'step_status'),
        Index('idx_task_category', 'category'),
    )

# ==================== 合同模型 (电子契约) ====================

class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_token = Column(String(32), unique=True,
                           default=lambda: "CTR_" + secrets.token_hex(4).upper())
    
    task_id = Column(String(36), ForeignKey("tasks.id"), unique=True, nullable=False)
    task = relationship("Task", back_populates="contract")
    
    # 双方信息
    publisher_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    publisher = relationship("User", foreign_keys=[publisher_id], back_populates="contracts")
    acceptor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    acceptor = relationship("User", foreign_keys=[acceptor_id], back_populates="signed_contracts")
    
    # 合同内容
    contract_content = Column(Text, nullable=False)           # 合同文本
    content_hash = Column(String(64), nullable=False)         # 内容SHA256哈希
    
    # 电子签名
    publisher_signature = Column(String(500), nullable=True)  # 发布方签名数据
    publisher_signed_at = Column(DateTime, nullable=True)
    acceptor_signature = Column(String(500), nullable=True)   # 接单方签名数据
    acceptor_signed_at = Column(DateTime, nullable=True)
    
    # 区块链存证
    blockchain_tx_hash = Column(String(100), nullable=True)   # 区块链交易哈希
    smart_contract_address = Column(String(100), nullable=True)
    
    # 状态
    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)              # 合同过期时间

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
    content_hash = Column(String(64), nullable=False)         # 完整性校验
    
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
    is_visible = Column(Boolean, default=False)               # 互评后才可见
    
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

# ==================== 纠纷仲裁模型 ====================

class Dispute(Base):
    __tablename__ = "disputes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dispute_token = Column(String(32), unique=True,
                          default=lambda: "DSP_" + secrets.token_hex(4).upper())
    
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", backref="disputes")
    
    # 纠纷发起方
    initiated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    initiator = relationship("User", foreign_keys=[initiated_by])
    
    # 纠纷原因
    reason = Column(Text, nullable=False)
    reason_category = Column(String(50), nullable=False)  # quality_delay, not_as_described, etc.
    
    # 证据哈希（不存储实际内容，只存哈希用于验证）
    evidence_hashes = Column(JSON, default=list)  # [{type, hash, timestamp, description}]
    
    # 聊天指纹证据
    chat_fingerprint = Column(String(128), nullable=True)  # 关键聊天内容的哈希指纹
    chat_evidence_summary = Column(Text, nullable=True)    # 聊天证据摘要（动作和意图）
    
    # 纠纷状态
    status = Column(Enum(DisputeStatus), default=DisputeStatus.OPEN)
    resolution = Column(Enum(DisputeResolution), default=DisputeResolution.PENDING)
    
    # 处理信息
    assigned_agent = Column(String(36), ForeignKey("users.id"), nullable=True)  # 分配的客服
    agent_notes = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_dispute_task', 'task_id'),
        Index('idx_dispute_status', 'status'),
        Index('idx_dispute_agent', 'assigned_agent'),
    )

# ==================== 标准NDA模板模型 ====================

class NDATemplate(Base):
    __tablename__ = "nda_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # NDA内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)  # 内容哈希
    
    # 版本控制
    version = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # 适用场景
    applicable_privacy_levels = Column(JSON, default=list)  # [1, 2] 适用于哪些隐私等级
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== 用户NDA签署记录 ====================

class UserNDASign(Base):
    __tablename__ = "user_nda_signs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user = relationship("User")
    
    nda_template_id = Column(String(36), ForeignKey("nda_templates.id"), nullable=False)
    nda_template = relationship("NDATemplate")
    
    # 电子签名
    signature_data = Column(String(500), nullable=False)
    signed_content_hash = Column(String(64), nullable=False)
    
    # 签署时间
    signed_at = Column(DateTime, default=datetime.utcnow)
    
    # 区块链存证（可选）
    blockchain_tx_hash = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_nda_user_template', 'user_id', 'nda_template_id', unique=True),
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
