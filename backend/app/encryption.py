"""
第二人生平台 - 加密服务
实现PRD中的动态内容解密机制
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os
import hashlib
import secrets
from typing import Optional

class EncryptionService:
    """AES-256-GCM 加密服务"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        if master_key is None:
            master_key = os.urandom(32)
        elif len(master_key) != 32:
            raise ValueError("主密钥必须是32字节")
        self.master_key = master_key
    
    def _derive_key(self, salt: bytes, context: str = "default") -> bytes:
        """从主密钥派生特定用途的密钥"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=context.encode()
        )
        return hkdf.derive(self.master_key)
    
    def encrypt(self, plaintext: str, context: str = "content") -> str:
        """加密文本"""
        if not plaintext:
            return ""
        
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._derive_key(salt, context)
        
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        encrypted = salt + nonce + ciphertext
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_text: str, context: str = "content") -> str:
        """解密文本"""
        if not encrypted_text:
            return ""
        
        try:
            encrypted = base64.b64decode(encrypted_text)
            salt = encrypted[:16]
            nonce = encrypted[16:28]
            ciphertext = encrypted[28:]
            
            key = self._derive_key(salt, context)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode()
        except Exception:
            return "[内容不可访问]"
    
    def hash_data(self, data: str) -> str:
        """SHA-256 哈希"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def generate_token(self, prefix: str = "SL") -> str:
        """生成安全随机令牌"""
        return f"{prefix}_{secrets.token_hex(4).upper()}"

class ContentAccessController:
    """内容访问控制器 - 实现动态内容解密"""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def check_access_permission(
        self, 
        user_level: int, 
        has_deposit: bool, 
        min_required_level: int,
        is_invited: bool = False,
        visibility_level: str = "l1"
    ) -> dict:
        """
        检查用户是否有权限访问内容
        
        规则:
        - L1: 所有人可见
        - L2: 需要等级达标或有保证金
        - L3: 需要被邀请
        - L4: 需要是任务参与方
        """
        result = {
            "can_view_full": False,
            "reason": None,
            "unlock_requirements": {}
        }
        
        if visibility_level == "l1":
            result["can_view_full"] = True
        elif visibility_level == "l2":
            if user_level >= min_required_level or has_deposit:
                result["can_view_full"] = True
            else:
                result["reason"] = "insufficient_permission"
                result["unlock_requirements"] = {
                    "min_level": min_required_level,
                    "need_deposit": not has_deposit
                }
        elif visibility_level == "l3":
            if is_invited:
                result["can_view_full"] = True
            else:
                result["reason"] = "invitation_only"
        elif visibility_level == "l4":
            # L4任务需要接受后才能查看
            result["reason"] = "anonymous_task"
            result["unlock_requirements"] = {"need_accept": True}
        
        return result
    
    def mask_sensitive_info(self, content: str) -> str:
        """脱敏处理 - 遮蔽联系方式"""
        import re
        
        masked = content
        
        # 手机号脱敏: 138****1234
        phone_pattern = r'1[3-9]\d{9}'
        masked = re.sub(phone_pattern, lambda m: m.group()[:3] + '****' + m.group()[-4:], masked)
        
        # 邮箱脱敏: a***@example.com
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        def mask_email(match):
            email = match.group()
            local, domain = email.split('@')
            if len(local) > 2:
                return local[0] + '***@' + domain
            return '***@' + domain
        masked = re.sub(email_pattern, mask_email, masked)
        
        # 身份证号脱敏
        id_pattern = r'\d{17}[\dXx]|\d{15}'
        masked = re.sub(id_pattern, lambda m: m.group()[:6] + '********' + m.group()[-4:], masked)
        
        return masked

# 全局加密服务实例
encryption_service = EncryptionService()
content_controller = ContentAccessController(encryption_service)
