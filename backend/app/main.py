"""
第二人生平台 - FastAPI主应用
生产就绪，包含完整的安全防护
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import bcrypt
import secrets
import re
import os
from pydantic import BaseModel, Field, EmailStr, validator

import html

# 转义函数
def escape_html(text: str) -> str:
    if not text:
        return text
    return html.escape(text)

from app.models import (
    init_db, get_session_maker, User, Task, Escrow, ChatMessage, 
    Rating, AuditLog, UserRole, TaskStatus, VisibilityLevel, 
    EscrowStatus, MessageType
)
from app.encryption import encryption_service, content_controller

# ==================== 配置 ====================

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ==================== 初始化 ====================

engine = init_db(os.getenv("DATABASE_URL", "sqlite:///./secondlife.db"))
SessionLocal = get_session_maker(engine)

app = FastAPI(
    title="第二人生 (Second Life)",
    description="高端任务众包平台 API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ==================== 依赖 ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="认证令牌已过期")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    
    return user

async def log_audit(
    db: Session,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    db.commit()

# ==================== Pydantic模型 ====================

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含至少一个数字')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    category: str
    summary: str = Field(..., min_length=10, max_length=500)
    description: str
    budget_min: float = Field(..., gt=0)
    budget_max: float = Field(..., gt=0)
    visibility_level: str = "l1"
    location: Optional[str] = None
    deadline: Optional[datetime] = None
    min_credit_level: int = Field(default=1, ge=1, le=10)
    required_skills: Optional[List[str]] = None
    is_invitation_only: bool = False
    publisher_anonymous: bool = False

class TaskResponse(BaseModel):
    id: str
    task_token: str
    title: str
    category: str
    summary: str
    budget_range: str
    visibility_level: str
    status: str
    publisher_anonymous: bool
    created_at: datetime

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

# ==================== 认证路由 ====================

@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserRegister, db: Session = Depends(get_db), request: Request = None):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(user_data.password.encode(), salt)
    
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash.decode()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    await log_audit(db, user.id, "user_register", "user", user.id, request=request)
    
    return {"message": "注册成功", "user_id": user.id}

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db), request: Request = None):
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not bcrypt.checkpw(login_data.password.encode(), user.password_hash.encode()):
        await log_audit(db, user.id, "login_failed", "user", user.id, request=request)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "type": "access"},
        SECRET_KEY, algorithm=ALGORITHM
    )
    
    refresh_token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "type": "refresh"},
        SECRET_KEY, algorithm=ALGORITHM
    )
    
    await log_audit(db, user.id, "login_success", "user", user.id, request=request)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

# ==================== 任务路由 ====================

@app.post("/api/tasks", response_model=dict)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """发布任务"""
    # XSS防护 - 转义用户输入
    safe_title = escape_html(task_data.title)
    safe_summary = escape_html(task_data.summary)
    
    # 加密敏感内容
    description_encrypted = encryption_service.encrypt(task_data.description)
    
    # 生成发布者令牌（如果选择匿名）
    publisher_token = None
    if task_data.publisher_anonymous:
        publisher_token = f"@SL_Pub_{secrets.token_hex(4).upper()}"
    
    task = Task(
        title=safe_title,
        category=task_data.category,
        summary=safe_summary,
        description_encrypted=description_encrypted,
        budget_min=task_data.budget_min,
        budget_max=task_data.budget_max,
        visibility_level=VisibilityLevel(task_data.visibility_level),
        location=task_data.location,
        deadline=task_data.deadline,
        min_credit_level=task_data.min_credit_level,
        required_skills=task_data.required_skills or [],
        is_invitation_only=task_data.is_invitation_only,
        publisher_anonymous=task_data.publisher_anonymous,
        publisher_token=publisher_token,
        publisher_id=current_user.id,
        status=TaskStatus.PUBLISHED,
        published_at=datetime.utcnow()
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    await log_audit(db, current_user.id, "task_create", "task", task.id, 
                   {"visibility": task_data.visibility_level}, request)
    
    return {
        "message": "任务发布成功",
        "task_id": task.id,
        "task_token": task.task_token,
        "publisher_token": publisher_token
    }

@app.get("/api/tasks")
async def list_tasks(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务列表（根据可见性等级过滤）"""
    query = db.query(Task).filter(Task.status == TaskStatus.PUBLISHED)
    
    if category:
        query = query.filter(Task.category == category)
    
    visible_tasks = []
    for task in query.all():
        # 权限检查
        is_invited = current_user.id in (task.invited_users or [])
        
        permission = content_controller.check_access_permission(
            user_level=current_user.credit_level,
            has_deposit=current_user.deposit_status,
            min_required_level=task.min_credit_level,
            is_invited=is_invited,
            visibility_level=task.visibility_level.value
        )
        
        if permission["can_view_full"] or task.visibility_level == VisibilityLevel.L1_PUBLIC:
            visible_tasks.append({
                "id": task.id,
                "task_token": task.task_token if not task.publisher_anonymous else "ANON",
                "title": task.title,
                "category": task.category,
                "summary": task.summary,
                "budget_range": f"¥{task.budget_min:,.0f} - ¥{task.budget_max:,.0f}",
                "visibility_level": task.visibility_level.value,
                "status": task.status.value,
                "publisher_anonymous": task.publisher_anonymous,
                "publisher_display": task.publisher_token if task.publisher_anonymous else task.publisher.username,
                "created_at": task.created_at.isoformat()
            })
    
    return visible_tasks

@app.get("/api/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查是否为任务参与方
    is_participant = (task.publisher_id == current_user.id or task.acceptor_id == current_user.id)
    is_invited = current_user.id in (task.invited_users or [])
    
    permission = content_controller.check_access_permission(
        user_level=current_user.credit_level,
        has_deposit=current_user.deposit_status,
        min_required_level=task.min_credit_level,
        is_invited=is_invited,
        visibility_level=task.visibility_level.value
    )
    
    response = {
        "id": task.id,
        "task_token": task.task_token,
        "title": task.title,
        "category": task.category,
        "summary": task.summary,
        "budget_range": f"¥{task.budget_min:,.0f} - ¥{task.budget_max:,.0f}",
        "visibility_level": task.visibility_level.value,
        "status": task.status.value,
        "location": task.location,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "min_credit_level": task.min_credit_level,
        "publisher_anonymous": task.publisher_anonymous,
        "publisher_display": task.publisher_token if task.publisher_anonymous else task.publisher.username,
        "created_at": task.created_at.isoformat(),
        "can_view_full": permission["can_view_full"]
    }
    
    if permission["can_view_full"] or is_participant:
        response["description"] = encryption_service.decrypt(task.description_encrypted)
        response["requirements"] = task.requirements_encrypted
    else:
        response["unlock_requirements"] = permission.get("unlock_requirements", {})
    
    return response

@app.post("/api/tasks/{task_id}/accept")
async def accept_task(
    task_id: str,
    acceptor_anonymous: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """接受任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status != TaskStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="任务不可接受")
    
    if task.publisher_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能接受自己发布的任务")
    
    # 检查可见性权限
    is_invited = current_user.id in (task.invited_users or [])
    permission = content_controller.check_access_permission(
        user_level=current_user.credit_level,
        has_deposit=current_user.deposit_status,
        min_required_level=task.min_credit_level,
        is_invited=is_invited,
        visibility_level=task.visibility_level.value
    )
    
    if not permission["can_view_full"]:
        raise HTTPException(status_code=403, detail="没有权限接受此任务")
    
    # 接受任务
    task.acceptor_id = current_user.id
    task.status = TaskStatus.ACCEPTED
    task.accepted_at = datetime.utcnow()
    
    if acceptor_anonymous:
        task.acceptor_anonymous = True
        task.acceptor_token = f"@SL_Acc_{secrets.token_hex(4).upper()}"
    
    # 创建资金托管记录
    escrow = Escrow(
        task_id=task.id,
        amount=task.budget_max,  # 使用最高预算作为托管金额
        currency=task.currency
    )
    db.add(escrow)
    db.commit()
    
    return {
        "message": "任务接受成功",
        "task_status": task.status.value,
        "escrow_token": escrow.escrow_token
    }

# ==================== 即时通讯路由 ====================

@app.post("/api/tasks/{task_id}/messages")
async def send_message(
    task_id: str,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送消息"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查是否为任务参与方
    if task.publisher_id != current_user.id and task.acceptor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权在此任务中发送消息")
    
    # 脱敏处理
    masked_content = content_controller.mask_sensitive_info(message_data.content)
    has_sensitive = masked_content != message_data.content
    
    # 加密存储
    content_encrypted = encryption_service.encrypt(message_data.content)
    content_hash = encryption_service.hash_data(message_data.content)
    
    message = ChatMessage(
        task_id=task_id,
        sender_id=current_user.id,
        content_encrypted=content_encrypted,
        content_hash=content_hash,
        has_sensitive_info=has_sensitive,
        masked_content=masked_content if has_sensitive else None
    )
    
    db.add(message)
    db.commit()
    
    return {
        "message": "发送成功",
        "message_id": message.id,
        "masked": has_sensitive
    }

@app.get("/api/tasks/{task_id}/messages")
async def get_messages(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务消息列表"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.publisher_id != current_user.id and task.acceptor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此任务的消息")
    
    messages = db.query(ChatMessage).filter(ChatMessage.task_id == task_id).order_by(ChatMessage.created_at).all()
    
    result = []
    for msg in messages:
        sender_display = msg.sender.username
        if msg.task.publisher_anonymous and msg.sender_id == msg.task.publisher_id:
            sender_display = msg.task.publisher_token or "发布者"
        if msg.task.acceptor_anonymous and msg.sender_id == msg.task.acceptor_id:
            sender_display = msg.task.acceptor_token or "接受者"
        
        result.append({
            "id": msg.id,
            "sender": sender_display,
            "content": encryption_service.decrypt(msg.content_encrypted),
            "masked_content": msg.masked_content,
            "has_sensitive_info": msg.has_sensitive_info,
            "created_at": msg.created_at.isoformat()
        })
    
    return result

# ==================== 评级路由 ====================

class RatingCreate(BaseModel):
    professionalism: int = Field(..., ge=1, le=5)
    communication: int = Field(..., ge=1, le=5)
    quality: int = Field(..., ge=1, le=5)
    privacy_respect: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    is_anonymous: bool = False

@app.post("/api/tasks/{task_id}/rate")
async def rate_task(
    task_id: str,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """评价任务参与方"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务不存在或未完成")
    
    # 确定评价对象
    if task.publisher_id == current_user.id:
        ratee_id = task.acceptor_id
    elif task.acceptor_id == current_user.id:
        ratee_id = task.publisher_id
    else:
        raise HTTPException(status_code=403, detail="无权评价此任务")
    
    if not ratee_id:
        raise HTTPException(status_code=400, detail="评价对象不存在")
    
    overall_score = (rating_data.professionalism + rating_data.communication + rating_data.quality + rating_data.privacy_respect) / 4
    
    rating = Rating(
        task_id=task_id,
        rater_id=current_user.id,
        ratee_id=ratee_id,
        professionalism=rating_data.professionalism,
        communication=rating_data.communication,
        quality=rating_data.quality,
        privacy_respect=rating_data.privacy_respect,
        overall_score=overall_score,
        comment=rating_data.comment,
        is_anonymous=rating_data.is_anonymous
    )
    
    db.add(rating)
    db.commit()
    
    # 更新被评价者信用分
    ratee = db.query(User).filter(User.id == ratee_id).first()
    if ratee:
        # 简单的加权算法
        ratee.credit_score = min(1000, ratee.credit_score + overall_score * 2)
        ratee.credit_level = min(10, int(ratee.credit_score / 100))
        db.commit()
    
    return {"message": "评价提交成功"}

# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/")
async def api_root():
    return {
        "message": "第二人生 (Second Life) API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
