"""
第二人生平台 V2.0 - 7步流程状态机
核心云函数: handleTaskFlow
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import json
import re

class TaskFlowError(Exception):
    """流程错误"""
    pass

class TaskFlowManager:
    """
    7步流程状态机管理器
    
    步骤:
    1. 发布 (Publish)   -> AI自动审核敏感词
    2. 审核 (Verify)    -> 管理员/AI判定真实性
    3. 接单 (Apply)     -> 接受者提交简历/数字名片
    4. 签约 (Contract)  -> 双方滑动确认，生成电子契约
    5. 交付 (Submit)    -> 上传证据链（照片/视频/代码链接）
    6. 验收 (Accept)    -> 发布方确认，触发支付
    7. 结算 (Settle)    -> 资金划转，平台抽成
    """
    
    # 步骤流转规则: 当前步骤 -> [允许的操作 -> 目标步骤]
    FLOW_RULES = {
        1: {  # 发布
            "ai_review": 2,           # AI审核通过 -> 审核
            "cancel": None,           # 取消 -> 结束
        },
        2: {  # 审核
            "admin_approve": 3,       # 管理员通过 -> 接单
            "admin_reject": None,     # 拒绝 -> 结束
            "auto_approve": 3,        # 自动通过 -> 接单
        },
        3: {  # 接单
            "accept": 4,              # 接受任务 -> 签约
            "expire": None,           # 过期 -> 结束
        },
        4: {  # 签约
            "publisher_sign": 4,      # 发布方签署 (等待接单方)
            "acceptor_sign": 5,       # 接单方签署 -> 交付
            "cancel": None,           # 取消 -> 结束
        },
        5: {  # 交付
            "submit": 6,              # 提交交付物 -> 验收
            "dispute": None,          # 争议 -> 仲裁
        },
        6: {  # 验收
            "confirm": 7,             # 确认通过 -> 结算
            "reject": 5,              # 拒绝 -> 重新交付
            "dispute": None,          # 争议 -> 仲裁
        },
        7: {  # 结算
            "settle": None,           # 结算完成 -> 结束
        }
    }
    
    # 敏感词列表 (AI审核用)
    SENSITIVE_WORDS = [
        "诈骗", "欺诈", "洗钱", "赌博", "毒品", "色情", "暴力", "恐怖",
        "黑客", "攻击", "窃取", "盗取", "伪造", "假冒", "冒充",
        "违法", "犯罪", "走私", "贩卖", "枪支", "弹药", "爆炸物",
    ]
    
    def __init__(self, db_session):
        self.db = db_session
    
    # ========== Step 1: 发布 ==========
    
    def step1_publish(self, task_data: Dict[str, Any], publisher_id: str) -> Tuple[bool, str, Dict]:
        """
        发布任务
        - AI自动审核敏感词
        - 存入数据库
        """
        # AI敏感词审核
        content_to_check = f"{task_data.get('title', '')} {task_data.get('summary', '')} {task_data.get('description', '')}"
        ai_review_result = self._ai_sensitive_word_check(content_to_check)
        
        if ai_review_result["has_sensitive"]:
            return False, f"AI审核失败：检测到敏感词 {ai_review_result['words']}", ai_review_result
        
        # 创建任务
        from app.models import Task, TaskStatus
        
        task = Task(
            publisher_id=publisher_id,
            title=task_data["title"],
            category=task_data["category"],
            summary=task_data["summary"],
            description_encrypted=task_data.get("description", ""),  # 应该加密
            budget_min=task_data["budget_min"],
            budget_max=task_data["budget_max"],
            visibility_level=task_data.get("visibility_level", "l1"),
            privacy_level=task_data.get("privacy_level", 0),
            nda_required=task_data.get("nda_required", False),
            min_credit_level=task_data.get("min_credit_level", 1),
            required_skills=task_data.get("required_skills", []),
            is_invitation_only=task_data.get("is_invitation_only", False),
            invited_users=task_data.get("invited_users", []),
            publisher_anonymous=task_data.get("publisher_anonymous", False),
            step_status=1,
            status=TaskStatus.PENDING_REVIEW,
            ai_reviewed=True,
            ai_review_result=ai_review_result,
            created_at=datetime.utcnow()
        )
        
        # 生成发布者匿名令牌
        if task.publisher_anonymous:
            import secrets
            task.publisher_token = f"@SL_Pub_{secrets.token_hex(4).upper()}"
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        # 自动触发步骤流转到审核
        return self.transition(task.id, "ai_review", {"review_result": ai_review_result})
    
    def _ai_sensitive_word_check(self, content: str) -> Dict:
        """AI敏感词检测"""
        content_lower = content.lower()
        found_words = []
        
        for word in self.SENSITIVE_WORDS:
            if word in content_lower:
                found_words.append(word)
        
        # 计算风险分数
        risk_score = len(found_words) * 20  # 每个敏感词20分
        
        return {
            "has_sensitive": len(found_words) > 0,
            "words": found_words,
            "risk_score": min(risk_score, 100),
            "reviewed_at": datetime.utcnow().isoformat()
        }
    
    # ========== Step 2: 审核 ==========
    
    def step2_verify(self, task_id: str, admin_id: str, decision: str, notes: str = "") -> Tuple[bool, str, Dict]:
        """
        管理员审核
        - 判定任务真实性
        """
        from app.models import Task, TaskStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        if task.step_status != 2:
            return False, f"任务当前不在审核阶段 (当前步骤: {task.step_status})", {}
        
        if decision == "approve":
            task.admin_reviewed = True
            task.admin_notes = notes
            task.verified_at = datetime.utcnow()
            self.db.commit()
            
            # 流转到接单阶段
            return self.transition(task_id, "admin_approve", {"admin_id": admin_id, "notes": notes})
        
        elif decision == "reject":
            task.status = TaskStatus.CANCELLED
            task.admin_notes = notes
            self.db.commit()
            return self.transition(task_id, "admin_reject", {"admin_id": admin_id, "notes": notes})
        
        else:
            return False, "无效的审核决定", {}
    
    # ========== Step 3: 接单 ==========
    
    def step3_apply(self, task_id: str, acceptor_id: str, application: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        """
        接单申请
        - 接受者提交简历/数字名片
        """
        from app.models import Task, TaskStatus, User
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        if task.step_status != 3:
            return False, f"任务当前不在接单阶段 (当前步骤: {task.step_status})", {}
        
        if task.publisher_id == acceptor_id:
            return False, "不能接自己的任务", {}
        
        # 检查资格要求
        acceptor = self.db.query(User).filter(User.id == acceptor_id).first()
        if not acceptor:
            return False, "用户不存在", {}
        
        if acceptor.credit_level < task.min_credit_level:
            return False, f"信用等级不足 (需要{task.min_credit_level}级，当前{acceptor.credit_level}级)", {}
        
        # 检查NDA要求
        if task.nda_required and not task.nda_signed_by_acceptor:
            return False, "需要先签署NDA", {}
        
        # 更新任务状态
        task.acceptor_id = acceptor_id
        task.accepted_at = datetime.utcnow()
        task.status = TaskStatus.ACCEPTED
        
        # 生成接单方匿名令牌
        if application.get("acceptor_anonymous", False):
            import secrets
            task.acceptor_anonymous = True
            task.acceptor_token = f"@SL_Acc_{secrets.token_hex(4).upper()}"
        
        self.db.commit()
        
        # 流转到签约阶段
        return self.transition(task_id, "accept", {
            "acceptor_id": acceptor_id,
            "application": application
        })
    
    # ========== Step 4: 签约 ==========
    
    def step4_contract_sign(self, task_id: str, user_id: str, signature_data: str, is_publisher: bool) -> Tuple[bool, str, Dict]:
        """
        签署电子合同
        - 双方滑动确认
        - 生成电子契约
        """
        from app.models import Task, Contract, ContractStatus
        import hashlib
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        if task.step_status != 4:
            return False, f"任务当前不在签约阶段 (当前步骤: {task.step_status})", {}
        
        # 获取或创建合同
        contract = task.contract
        if not contract:
            # 生成合同内容
            contract_content = self._generate_contract_content(task)
            content_hash = hashlib.sha256(contract_content.encode()).hexdigest()
            
            contract = Contract(
                task_id=task_id,
                publisher_id=task.publisher_id,
                acceptor_id=task.acceptor_id,
                contract_content=contract_content,
                content_hash=content_hash,
                status=ContractStatus.PENDING_PUBLISHER
            )
            self.db.add(contract)
            self.db.commit()
        
        # 记录签名
        if is_publisher:
            if user_id != task.publisher_id:
                return False, "无权代表发布方签署", {}
            contract.publisher_signature = signature_data
            contract.publisher_signed_at = datetime.utcnow()
            contract.status = ContractStatus.PENDING_ACCEPTOR
        else:
            if user_id != task.acceptor_id:
                return False, "无权代表接单方签署", {}
            contract.acceptor_signature = signature_data
            contract.acceptor_signed_at = datetime.utcnow()
            contract.status = ContractStatus.SIGNED
        
        self.db.commit()
        
        # 如果双方都签署了，流转到交付阶段
        if contract.status == ContractStatus.SIGNED:
            task.contracted_at = datetime.utcnow()
            self.db.commit()
            return self.transition(task_id, "acceptor_sign", {"contract_id": contract.id})
        
        return True, "等待另一方签署", {"contract_status": contract.status.value}
    
    def _generate_contract_content(self, task) -> str:
        """生成合同内容"""
        return f"""
第二人生平台任务合同

任务编号: {task.task_token}
任务名称: {task.title}

发布方: {task.publisher.username}
接单方: {task.acceptor.username if task.acceptor else '待定'}

预算范围: ¥{task.budget_min} - ¥{task.budget_max}
交付期限: {task.deadline.strftime('%Y-%m-%d') if task.deadline else '待定'}

双方确认已阅读并同意平台服务条款。
本合同由第二人生平台电子签名系统见证。

生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # ========== Step 5: 交付 ==========
    
    def step5_submit(self, task_id: str, acceptor_id: str, deliverables: list) -> Tuple[bool, str, Dict]:
        """
        提交交付物
        - 上传证据链（照片/视频/代码链接）
        """
        from app.models import Task, TaskStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        if task.step_status != 5:
            return False, f"任务当前不在交付阶段 (当前步骤: {task.step_status})", {}
        
        if task.acceptor_id != acceptor_id:
            return False, "无权提交交付物", {}
        
        # 验证交付物
        validated_deliverables = []
        for item in deliverables:
            validated_item = {
                "type": item.get("type"),  # photo, video, code, document
                "url": item.get("url"),
                "hash": item.get("hash"),  # 文件哈希
                "description": item.get("description", ""),
                "submitted_at": datetime.utcnow().isoformat()
            }
            validated_deliverables.append(validated_item)
        
        task.deliverables = validated_deliverables
        task.submitted_at = datetime.utcnow()
        task.status = TaskStatus.DELIVERED
        self.db.commit()
        
        # 流转到验收阶段
        return self.transition(task_id, "submit", {"deliverables_count": len(deliverables)})
    
    # ========== Step 6: 验收 ==========
    
    def step6_accept(self, task_id: str, publisher_id: str, decision: str, feedback: str = "") -> Tuple[bool, str, Dict]:
        """
        验收交付物
        - 发布方确认
        - 触发支付逻辑
        """
        from app.models import Task, TaskStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        if task.step_status != 6:
            return False, f"任务当前不在验收阶段 (当前步骤: {task.step_status})", {}
        
        if task.publisher_id != publisher_id:
            return False, "无权验收", {}
        
        if decision == "confirm":
            task.accepted_by_publisher_at = datetime.utcnow()
            task.status = TaskStatus.COMPLETED
            self.db.commit()
            
            # 触发支付（创建托管释放记录）
            self._trigger_payment(task_id)
            
            # 流转到结算阶段
            return self.transition(task_id, "confirm", {"feedback": feedback})
        
        elif decision == "reject":
            task.status = TaskStatus.IN_PROGRESS
            self.db.commit()
            return self.transition(task_id, "reject", {"feedback": feedback})
        
        else:
            return False, "无效的决定", {}
    
    def _trigger_payment(self, task_id: str):
        """
        触发支付指令 - 平台不碰资金
        只向银行/支付机构发送释放指令，实际资金由第三方托管
        """
        from app.models import Escrow, EscrowStatus
        
        escrow = self.db.query(Escrow).filter(Escrow.task_id == task_id).first()
        if escrow and escrow.status == EscrowStatus.HELD_BY_BANK:
            # 平台只更新状态，实际资金操作由银行/支付机构完成
            escrow.status = EscrowStatus.RELEASED
            escrow.released_at = datetime.utcnow()
            # 这里会触发 webhook 通知银行释放资金
            self._notify_bank_release(escrow)
            self.db.commit()
    
    def _notify_bank_release(self, escrow):
        """通知银行释放资金 - webhook调用"""
        # 实际实现中调用银行/支付机构API
        import logging
        logging.info(f"[BANK_WEBHOOK] Release funds for escrow {escrow.escrow_token}")
    
    # ========== Step 7: 结算 ==========
    
    def step7_settle(self, task_id: str, bank_confirmation: Dict = None) -> Tuple[bool, str, Dict]:
        """
        资金结算确认
        - 接收银行/支付机构的结算确认
        - 平台记录结算完成，不处理资金
        """
        from app.models import Task, TaskStatus, Escrow, EscrowStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        if task.step_status != 7:
            return False, f"任务当前不在结算阶段 (当前步骤: {task.step_status})", {}
        
        # 验证银行确认
        escrow = self.db.query(Escrow).filter(Escrow.task_id == task_id).first()
        if not escrow or escrow.status != EscrowStatus.RELEASED:
            return False, "资金尚未释放，无法结算", {}
        
        # 银行/支付机构实际结算信息
        settlement_info = bank_confirmation or {
            "bank_tx_id": "BANK_TX_" + secrets.token_hex(8).upper(),
            "settled_at": datetime.utcnow().isoformat()
        }
        
        # 记录结算信息（平台不计算抽成，由银行/支付机构处理）
        task.settled_at = datetime.utcnow()
        task.completed_at = datetime.utcnow()
        task.status = TaskStatus.COMPLETED
        
        # 存储银行结算记录
        escrow.bank_settlement_info = settlement_info
        self.db.commit()
        
        return True, "结算完成", {
            "settled_at": task.settled_at.isoformat(),
            "bank_confirmation": settlement_info
        }
    
    # ========== 纠纷处理 ==========
    
    def open_dispute(self, task_id: str, user_id: str, reason: str, 
                     reason_category: str, evidence_hashes: list = None) -> Tuple[bool, str, Dict]:
        """
        开启纠纷
        - 冻结任务状态
        - 生成纠纷记录
        - 转入人工客服
        """
        from app.models import Task, TaskStatus, Dispute, DisputeStatus, Escrow, EscrowStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        # 检查权限（必须是参与方）
        if user_id not in [task.publisher_id, task.acceptor_id]:
            return False, "无权发起纠纷", {}
        
        # 冻结任务状态
        previous_status = task.status
        task.status = TaskStatus.DISPUTED
        
        # 冻结资金托管
        escrow = self.db.query(Escrow).filter(Escrow.task_id == task_id).first()
        if escrow:
            escrow.status = EscrowStatus.FROZEN
            self._notify_bank_freeze(escrow)
        
        # 收集聊天指纹证据
        chat_fingerprint = self._generate_chat_fingerprint(task_id)
        
        # 创建纠纷记录
        dispute = Dispute(
            task_id=task_id,
            initiated_by=user_id,
            reason=reason,
            reason_category=reason_category,
            evidence_hashes=evidence_hashes or [],
            chat_fingerprint=chat_fingerprint["fingerprint"],
            chat_evidence_summary=chat_fingerprint["summary"],
            status=DisputeStatus.OPEN
        )
        
        self.db.add(dispute)
        self.db.commit()
        
        # 通知客服团队
        self._notify_support_team(dispute)
        
        return True, "纠纷已开启，任务和资金已冻结", {
            "dispute_id": dispute.id,
            "dispute_token": dispute.dispute_token,
            "previous_status": previous_status.value,
            "frozen_escrow": escrow.escrow_token if escrow else None
        }
    
    def _notify_bank_freeze(self, escrow):
        """通知银行冻结资金"""
        import logging
        logging.info(f"[BANK_WEBHOOK] Freeze funds for escrow {escrow.escrow_token}")
    
    def _generate_chat_fingerprint(self, task_id: str) -> Dict:
        """
        生成聊天指纹证据
        不存储实际内容，只记录关键动作的哈希和时间戳
        """
        from app.models import ChatMessage
        import hashlib
        
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.task_id == task_id
        ).order_by(ChatMessage.created_at).all()
        
        fingerprint_parts = []
        action_summary = []
        
        for msg in messages:
            # 只记录关键动作（接单、签约、交付、验收等）
            content_lower = msg.content_hash.lower()
            
            # 关键动作关键词
            keywords = ["接受", "签署", "交付", "提交", "验收", "确认", "拒绝", "不同意"]
            for kw in keywords:
                if kw in content_lower or kw in str(msg.masked_content or ""):
                    fp = f"{msg.created_at.isoformat()}:{msg.sender_id[:8]}:{hashlib.sha256(msg.content_hash.encode()).hexdigest()[:16]}"
                    fingerprint_parts.append(fp)
                    action_summary.append(f"[{msg.created_at.strftime('%m-%d %H:%M')}] {kw}")
                    break
        
        full_fingerprint = hashlib.sha256(
            "|".join(fingerprint_parts).encode()
        ).hexdigest()
        
        return {
            "fingerprint": full_fingerprint,
            "summary": "; ".join(action_summary[-10:]) if action_summary else "无关键动作记录",
            "message_count": len(messages),
            "key_actions": len(action_summary)
        }
    
    def _notify_support_team(self, dispute):
        """通知人工客服团队"""
        import logging
        logging.info(f"[SUPPORT_ALERT] New dispute {dispute.dispute_token} - Category: {dispute.reason_category}")
        # 实际实现：发送邮件/短信/钉钉通知给客服团队
    
    def assign_dispute_agent(self, dispute_id: str, agent_id: str) -> Tuple[bool, str, Dict]:
        """分配纠纷处理客服"""
        from app.models import Dispute, DisputeStatus
        
        dispute = self.db.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            return False, "纠纷不存在", {}
        
        dispute.assigned_agent = agent_id
        dispute.status = DisputeStatus.UNDER_REVIEW
        dispute.reviewed_at = datetime.utcnow()
        self.db.commit()
        
        return True, f"已分配给客服 {agent_id}", {
            "dispute_token": dispute.dispute_token,
            "assigned_agent": agent_id
        }
    
    def resolve_dispute(self, dispute_id: str, agent_id: str, 
                       resolution: str, notes: str) -> Tuple[bool, str, Dict]:
        """
        解决纠纷
        - 人工客服根据聊天指纹和证据做出裁决
        - 通知银行执行资金操作
        """
        from app.models import Dispute, DisputeStatus, DisputeResolution
        from app.models import Task, TaskStatus, Escrow, EscrowStatus
        
        dispute = self.db.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            return False, "纠纷不存在", {}
        
        if dispute.assigned_agent != agent_id:
            return False, "无权处理此纠纷", {}
        
        # 更新纠纷状态
        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution = DisputeResolution(resolution)
        dispute.resolution_notes = notes
        dispute.resolved_at = datetime.utcnow()
        
        # 解冻任务和资金，执行裁决
        task = self.db.query(Task).filter(Task.id == dispute.task_id).first()
        escrow = self.db.query(Escrow).filter(Escrow.task_id == dispute.task_id).first()
        
        if resolution == DisputeResolution.RELEASE_TO_ACCEPTOR.value:
            # 释放给接单方
            if task:
                task.status = TaskStatus.COMPLETED
            if escrow:
                escrow.status = EscrowStatus.RELEASED
                self._notify_bank_release(escrow)
                
        elif resolution == DisputeResolution.REFUND_TO_PUBLISHER.value:
            # 退还给发布方
            if task:
                task.status = TaskStatus.CANCELLED
            if escrow:
                escrow.status = EscrowStatus.REFUNDED
                self._notify_bank_refund(escrow)
                
        elif resolution == DisputeResolution.SPLIT.value:
            # 部分分配（需要银行支持）
            if escrow:
                escrow.status = EscrowStatus.RELEASED  # 标记为已处理，实际由银行执行分割
                self._notify_bank_split(escrow)
        
        self.db.commit()
        
        return True, "纠纷已解决", {
            "dispute_token": dispute.dispute_token,
            "resolution": resolution,
            "task_status": task.status.value if task else None,
            "escrow_status": escrow.status.value if escrow else None
        }
    
    def _notify_bank_refund(self, escrow):
        """通知银行退款"""
        import logging
        logging.info(f"[BANK_WEBHOOK] Refund to publisher for escrow {escrow.escrow_token}")
    
    def _notify_bank_split(self, escrow):
        """通知银行分割资金"""
        import logging
        logging.info(f"[BANK_WEBHOOK] Split funds for escrow {escrow.escrow_token}")
    
    # ========== 核心流转函数 ==========
    
    def transition(self, task_id: str, action: str, context: Dict = None) -> Tuple[bool, str, Dict]:
        """
        核心状态流转函数
        """
        from app.models import Task
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, "任务不存在", {}
        
        current_step = task.step_status
        
        # 检查操作是否允许
        if current_step not in self.FLOW_RULES:
            return False, f"无效的当前步骤: {current_step}", {}
        
        step_rules = self.FLOW_RULES[current_step]
        if action not in step_rules:
            return False, f"步骤{current_step}不允许操作: {action}", {}
        
        next_step = step_rules[action]
        
        # 执行流转
        if next_step is None:
            # 流程结束
            return True, "流程已结束", {"final_step": current_step}
        
        task.step_status = next_step
        self.db.commit()
        
        return True, f"流转成功: 步骤{current_step} -> {next_step}", {
            "previous_step": current_step,
            "current_step": next_step,
            "action": action,
            "context": context or {}
        }
    
    def get_flow_status(self, task_id: str) -> Dict:
        """获取任务流程状态"""
        from app.models import Task
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "任务不存在"}
        
        step_names = {
            1: "发布",
            2: "审核",
            3: "接单",
            4: "签约",
            5: "交付",
            6: "验收",
            7: "结算"
        }
        
        return {
            "task_id": task_id,
            "task_token": task.task_token,
            "current_step": task.step_status,
            "step_name": step_names.get(task.step_status, "未知"),
            "status": task.status.value,
            "progress": f"{task.step_status}/7",
            "progress_percent": round(task.step_status / 7 * 100, 1),
            "timeline": {
                "published_at": task.published_at.isoformat() if task.published_at else None,
                "verified_at": task.verified_at.isoformat() if task.verified_at else None,
                "accepted_at": task.accepted_at.isoformat() if task.accepted_at else None,
                "contracted_at": task.contracted_at.isoformat() if task.contracted_at else None,
                "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
                "accepted_by_publisher_at": task.accepted_by_publisher_at.isoformat() if task.accepted_by_publisher_at else None,
                "settled_at": task.settled_at.isoformat() if task.settled_at else None,
            }
        }


# 便捷函数
def handle_task_flow():
    """云函数入口"""
    # 这里可以接入实际的云函数框架（如AWS Lambda、阿里云函数等）
    pass


# ========== NDA管理 ==========

class NDAManager:
    """标准NDA模板管理与电子签署"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_nda_template(self, title: str, content: str, applicable_levels: list) -> Tuple[bool, str, Dict]:
        """创建标准NDA模板"""
        from app.models import NDATemplate
        import hashlib
        
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # 获取最新版本号
        latest = self.db.query(NDATemplate).order_by(NDATemplate.created_at.desc()).first()
        version = "1.0" if not latest else str(float(latest.version) + 1.0)
        
        nda = NDATemplate(
            title=title,
            content=content,
            content_hash=content_hash,
            version=version,
            applicable_privacy_levels=applicable_levels,
            is_active=True
        )
        
        # 禁用旧版本
        if latest:
            latest.is_active = False
        
        self.db.add(nda)
        self.db.commit()
        
        return True, "NDA模板创建成功", {
            "nda_id": nda.id,
            "version": version,
            "content_hash": content_hash[:16] + "..."
        }
    
    def get_standard_nda(self, privacy_level: int = 2) -> Tuple[bool, str, Dict]:
        """获取适用的标准NDA"""
        from app.models import NDATemplate
        
        nda = self.db.query(NDATemplate).filter(
            NDATemplate.is_active == True,
            NDATemplate.applicable_privacy_levels.contains([privacy_level])
        ).first()
        
        if not nda:
            # 返回默认NDA
            default_content = self._get_default_nda_content()
            return True, "使用默认NDA", {
                "content": default_content,
                "version": "default",
                "is_default": True
            }
        
        return True, "NDA模板获取成功", {
            "nda_id": nda.id,
            "title": nda.title,
            "content": nda.content,
            "version": nda.version,
            "content_hash": nda.content_hash[:16] + "...",
            "is_default": False
        }
    
    def _get_default_nda_content(self) -> str:
        """默认NDA内容"""
        return """
第二人生平台保密协议（NDA）

本协议由以下双方于签署日期签订：

披露方：任务发布方
接收方：任务接单方

1. 保密信息定义
接收方同意对从披露方获得的所有非公开信息保密。

2. 保密义务
接收方不得向任何第三方披露保密信息。

3. 使用限制
保密信息仅用于完成本任务目的。

4. 期限
保密义务自签署之日起生效，有效期为3年。

5. 违约责任
违反本协议的一方应承担相应的法律责任。

本协议通过第二人生平台电子签名系统签署，具有法律效力。
"""
    
    def sign_nda(self, user_id: str, nda_template_id: str = None, 
                 signature_data: str = None, privacy_level: int = 2) -> Tuple[bool, str, Dict]:
        """
        用户签署NDA
        - 使用标准版NDA
        - 电子签名
        """
        from app.models import NDATemplate, UserNDASign
        from app.models import User
        import hashlib
        import secrets
        
        # 获取用户
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "用户不存在", {}
        
        # 获取NDA模板
        if nda_template_id:
            nda = self.db.query(NDATemplate).filter(NDATemplate.id == nda_template_id).first()
        else:
            nda = self.db.query(NDATemplate).filter(
                NDATemplate.is_active == True,
                NDATemplate.applicable_privacy_levels.contains([privacy_level])
            ).first()
        
        if not nda:
            # 使用默认NDA
            default_content = self._get_default_nda_content()
            content_hash = hashlib.sha256(default_content.encode()).hexdigest()
        else:
            content_hash = nda.content_hash
        
        # 检查是否已签署
        existing = self.db.query(UserNDASign).filter(
            UserNDASign.user_id == user_id,
            UserNDASign.signed_content_hash == content_hash
        ).first()
        
        if existing:
            return True, "NDA已签署", {
                "sign_id": existing.id,
                "signed_at": existing.signed_at.isoformat()
            }
        
        # 生成签名数据（如果未提供）
        if not signature_data:
            sign_payload = f"{user_id}:{content_hash}:{datetime.utcnow().isoformat()}"
            signature_data = hashlib.sha256(sign_payload.encode()).hexdigest()
        
        # 创建签署记录
        nda_sign = UserNDASign(
            user_id=user_id,
            nda_template_id=nda.id if nda else None,
            signature_data=signature_data,
            signed_content_hash=content_hash,
            blockchain_tx_hash=None  # 可选：上链存证
        )
        
        self.db.add(nda_sign)
        self.db.commit()
        
        return True, "NDA签署成功", {
            "sign_id": nda_sign.id,
            "signature": signature_data[:32] + "...",
            "content_hash": content_hash[:16] + "...",
            "signed_at": nda_sign.signed_at.isoformat()
        }
    
    def verify_nda_signed(self, user_id: str, privacy_level: int = 2) -> Tuple[bool, str, Dict]:
        """验证用户是否已签署所需NDA"""
        from app.models import NDATemplate, UserNDASign
        
        # 获取当前适用的NDA
        nda = self.db.query(NDATemplate).filter(
            NDATemplate.is_active == True,
            NDATemplate.applicable_privacy_levels.contains([privacy_level])
        ).first()
        
        if not nda:
            # 检查是否签署了默认NDA
            default_content = self._get_default_nda_content()
            import hashlib
            default_hash = hashlib.sha256(default_content.encode()).hexdigest()
            
            signed = self.db.query(UserNDASign).filter(
                UserNDASign.user_id == user_id,
                UserNDASign.signed_content_hash == default_hash
            ).first()
        else:
            signed = self.db.query(UserNDASign).filter(
                UserNDASign.user_id == user_id,
                UserNDASign.nda_template_id == nda.id
            ).first()
        
        if signed:
            return True, "已签署NDA", {
                "signed": True,
                "signed_at": signed.signed_at.isoformat()
            }
        
        return False, "未签署NDA", {"signed": False}
