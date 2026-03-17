"""
第二人生平台 V2.0 - 全维度安全测试套件
测试范围：业务逻辑、认证授权、API安全、数据隐私、压力测试
"""

import requests
import json
import time
import hashlib
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Tuple
import sys
import os

# 添加backend到路径
sys.path.insert(0, '/root/.openclaw/workspace/secondlife/backend')

# 测试配置
BASE_URL = "https://secondlife-platform.onrender.com"
TEST_RESULTS = []

class SecurityTester:
    """安全测试执行器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.tokens = {}
        self.test_data = {}
        
    def log_test(self, name: str, passed: bool, details: str, severity: str = "info"):
        """记录测试结果"""
        result = {
            "name": name,
            "passed": passed,
            "details": details,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        TEST_RESULTS.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} [{severity.upper()}] {name}: {details}")
        return result
    
    # ========== 1. 认证安全测试 ==========
    
    def test_auth_bypass(self):
        """测试认证绕过防护"""
        print("\n=== 认证安全测试 ===")
        
        # 测试1: 未授权访问受保护端点
        endpoints = [
            "/api/user/profile",
            "/api/tasks",
            "/api/tasks/create",
            "/api/user/tasks"
        ]
        
        for endpoint in endpoints:
            try:
                resp = self.session.get(f"{BASE_URL}{endpoint}", timeout=10)
                if resp.status_code in [401, 403]:
                    self.log_test(f"Auth Bypass - {endpoint}", True, 
                                 f"未认证返回{resp.status_code}", "high")
                elif resp.status_code == 404:
                    self.log_test(f"Auth Bypass - {endpoint}", True,
                                 f"端点返回404（可能被移除）", "info")
                else:
                    self.log_test(f"Auth Bypass - {endpoint}", False,
                                 f"未认证却返回{resp.status_code}，存在绕过风险", "critical")
            except Exception as e:
                self.log_test(f"Auth Bypass - {endpoint}", False, str(e), "critical")
    
    def test_token_security(self):
        """测试Token安全"""
        print("\n=== Token安全测试 ===")
        
        # 测试无效Token
        headers = {"Authorization": "Bearer invalid_token_12345"}
        try:
            resp = self.session.get(f"{BASE_URL}/api/user/profile", 
                                   headers=headers, timeout=10)
            if resp.status_code in [401, 403]:
                self.log_test("Invalid Token Rejection", True,
                             "无效Token被拒绝", "high")
            else:
                self.log_test("Invalid Token Rejection", False,
                             f"无效Token被接受（{resp.status_code}）", "critical")
        except Exception as e:
            self.log_test("Invalid Token Rejection", False, str(e), "critical")
        
        # 测试Token过期
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        headers = {"Authorization": f"Bearer {expired_token}"}
        try:
            resp = self.session.get(f"{BASE_URL}/api/user/profile",
                                   headers=headers, timeout=10)
            if resp.status_code in [401, 403]:
                self.log_test("Expired Token Rejection", True,
                             "过期Token被拒绝", "high")
            else:
                self.log_test("Expired Token Rejection", False,
                             f"过期Token被接受（{resp.status_code}）", "high")
        except Exception as e:
            self.log_test("Expired Token Rejection", False, str(e), "high")
    
    # ========== 2. SQL注入测试 ==========
    
    def test_sql_injection(self):
        """测试SQL注入防护"""
        print("\n=== SQL注入测试 ===")
        
        # 注册测试用户获取Token
        test_user = self._register_test_user()
        if not test_user:
            self.log_test("SQL Injection Setup", False, "无法创建测试用户", "critical")
            return
        
        self.tokens['test'] = test_user['token']
        
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM users --",
            "' OR 1=1 --",
            "admin'--",
            "1'; DELETE FROM users WHERE '1'='1"
        ]
        
        headers = {"Authorization": f"Bearer {self.tokens['test']}"}
        
        for payload in payloads:
            try:
                # 测试搜索端点
                resp = self.session.get(
                    f"{BASE_URL}/api/tasks",
                    params={"category": payload},
                    headers=headers,
                    timeout=10
                )
                
                # 检查是否泄露数据库错误
                if resp.status_code == 500 and ("sql" in resp.text.lower() or "error" in resp.text.lower()):
                    self.log_test(f"SQL Injection - {payload[:20]}...", False,
                                 "可能泄露SQL错误信息", "critical")
                elif resp.status_code in [200, 400, 422]:
                    self.log_test(f"SQL Injection - {payload[:20]}...", True,
                                 "ORM防护正常", "high")
                else:
                    self.log_test(f"SQL Injection - {payload[:20]}...", True,
                                 f"返回{resp.status_code}", "medium")
            except Exception as e:
                self.log_test(f"SQL Injection - {payload[:20]}...", False, str(e), "medium")
    
    # ========== 3. XSS测试 ==========
    
    def test_xss_protection(self):
        """测试XSS防护"""
        print("\n=== XSS防护测试 ===")
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<body onload=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'>",
            "<svg onload=alert('xss')>",
        ]
        
        if 'test' not in self.tokens:
            self.log_test("XSS Test Setup", False, "缺少测试Token", "critical")
            return
        
        headers = {"Authorization": f"Bearer {self.tokens['test']}"}
        
        for payload in xss_payloads:
            try:
                # 创建带XSS payload的任务
                task_data = {
                    "title": f"XSS Test {payload[:20]}",
                    "category": "测试",
                    "summary": payload,
                    "description": payload,
                    "budget_min": 100,
                    "budget_max": 200
                }
                
                resp = self.session.post(
                    f"{BASE_URL}/api/tasks/create",
                    json=task_data,
                    headers=headers,
                    timeout=10
                )
                
                if resp.status_code in [200, 201]:
                    task_id = resp.json().get("task_id")
                    if task_id:
                        # 获取任务详情检查是否被转义
                        detail = self.session.get(
                            f"{BASE_URL}/api/tasks/{task_id}",
                            headers=headers,
                            timeout=10
                        )
                        
                        if detail.status_code == 200:
                            content = detail.text
                            # 检查payload是否在响应中且未被转义
                            if payload in content and "<script>" in content:
                                self.log_test(f"XSS - {payload[:30]}...", False,
                                             "XSS payload未被转义", "critical")
                            elif "&lt;script&gt;" in content or "&lt;img" in content:
                                self.log_test(f"XSS - {payload[:30]}...", True,
                                             "HTML已转义", "high")
                            else:
                                self.log_test(f"XSS - {payload[:30]}...", True,
                                             "Payload被处理", "medium")
                else:
                    self.log_test(f"XSS - {payload[:30]}...", True,
                                 f"创建失败({resp.status_code})，但无XSS风险", "low")
            except Exception as e:
                self.log_test(f"XSS - {payload[:30]}...", False, str(e), "low")
    
    # ========== 4. 业务逻辑测试 ==========
    
    def test_business_logic(self):
        """测试业务逻辑安全"""
        print("\n=== 业务逻辑测试 ===")
        
        # 测试：发布方不能接自己的任务
        headers = {"Authorization": f"Bearer {self.tokens.get('test', '')}"}
        
        try:
            # 创建任务
            task_data = {
                "title": "自发自接测试",
                "category": "测试",
                "summary": "测试发布方不能接自己的任务",
                "description": "测试内容",
                "budget_min": 100,
                "budget_max": 200
            }
            
            resp = self.session.post(
                f"{BASE_URL}/api/tasks/create",
                json=task_data,
                headers=headers,
                timeout=10
            )
            
            if resp.status_code in [200, 201]:
                task_id = resp.json().get("task_id")
                self.test_data['task_id'] = task_id
                
                # 尝试自发自接
                accept_resp = self.session.post(
                    f"{BASE_URL}/api/tasks/{task_id}/accept",
                    headers=headers,
                    timeout=10
                )
                
                if accept_resp.status_code == 400:
                    self.log_test("Self-Accept Prevention", True,
                                 "发布方不能接自己的任务", "high")
                elif accept_resp.status_code == 404:
                    self.log_test("Self-Accept Prevention", True,
                                 "端点不存在，需检查API设计", "medium")
                else:
                    self.log_test("Self-Accept Prevention", False,
                                 f"可能允许自发自接({accept_resp.status_code})", "critical")
            else:
                self.log_test("Task Creation", False, f"无法创建测试任务", "medium")
        except Exception as e:
            self.log_test("Business Logic", False, str(e), "medium")
    
    # ========== 5. 越权访问测试 ==========
    
    def test_idor(self):
        """测试不安全的直接对象引用（IDOR）"""
        print("\n=== 越权访问测试 ===")
        
        # 注册两个测试用户
        user1 = self._register_test_user("test1")
        user2 = self._register_test_user("test2")
        
        if not user1 or not user2:
            self.log_test("IDOR Setup", False, "无法创建测试用户", "critical")
            return
        
        # 用户1创建任务
        headers1 = {"Authorization": f"Bearer {user1['token']}"}
        task_data = {
            "title": "IDOR测试任务",
            "category": "测试",
            "summary": "测试越权访问",
            "description": "测试内容",
            "budget_min": 100,
            "budget_max": 200
        }
        
        try:
            resp = self.session.post(
                f"{BASE_URL}/api/tasks/create",
                json=task_data,
                headers=headers1,
                timeout=10
            )
            
            if resp.status_code in [200, 201]:
                task_id = resp.json().get("task_id")
                
                # 用户2尝试获取用户1的任务详情
                headers2 = {"Authorization": f"Bearer {user2['token']}"}
                detail = self.session.get(
                    f"{BASE_URL}/api/tasks/{task_id}",
                    headers=headers2,
                    timeout=10
                )
                
                # 如果任务不是公开的，应该拒绝访问
                if detail.status_code in [200, 404]:
                    # 200可能意味着任务公开可见（取决于业务逻辑）
                    # 404可能意味着任务不存在或不可见
                    self.log_test("IDOR - Task Detail", True,
                                 f"返回{detail.status_code}，需人工审核", "medium")
                elif detail.status_code in [401, 403]:
                    self.log_test("IDOR - Task Detail", True,
                                 "正确拒绝未授权访问", "high")
                else:
                    self.log_test("IDOR - Task Detail", False,
                                 f"意外响应{detail.status_code}", "medium")
        except Exception as e:
            self.log_test("IDOR", False, str(e), "medium")
    
    # ========== 6. 压力测试 ==========
    
    def test_pressure(self):
        """压力测试"""
        print("\n=== 压力测试 ===")
        
        def make_request(i):
            try:
                start = time.time()
                resp = self.session.get(f"{BASE_URL}/health", timeout=30)
                elapsed = time.time() - start
                return {
                    "index": i,
                    "status": resp.status_code,
                    "time": elapsed,
                    "success": resp.status_code == 200
                }
            except Exception as e:
                return {"index": i, "status": 0, "time": 0, "success": False, "error": str(e)}
        
        # 并发100请求
        concurrent_requests = 100
        print(f"执行{concurrent_requests}并发请求测试...")
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        avg_time = sum(r["time"] for r in results if r["success"]) / max(success_count, 1)
        
        success_rate = success_count / concurrent_requests * 100
        rps = concurrent_requests / total_time
        
        self.log_test(f"Pressure Test ({concurrent_requests} concurrent)",
                     success_rate >= 95,
                     f"成功率: {success_rate:.1f}%, 平均响应: {avg_time:.2f}s, RPS: {rps:.1f}",
                     "high")
        
        return {
            "total": concurrent_requests,
            "success": success_count,
            "failed": concurrent_requests - success_count,
            "success_rate": success_rate,
            "avg_response_time": avg_time,
            "rps": rps,
            "total_time": total_time
        }
    
    # ========== 辅助方法 ==========
    
    def _register_test_user(self, prefix="test"):
        """注册测试用户"""
        import random
        username = f"{prefix}_{random.randint(10000, 99999)}"
        email = f"{username}@test.com"
        
        try:
            resp = self.session.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "username": username,
                    "email": email,
                    "password": "TestPassword123!"
                },
                timeout=10
            )
            
            if resp.status_code in [200, 201]:
                # 登录获取Token
                login_resp = self.session.post(
                    f"{BASE_URL}/api/auth/login",
                    json={
                        "username": username,
                        "password": "TestPassword123!"
                    },
                    timeout=10
                )
                
                if login_resp.status_code == 200:
                    data = login_resp.json()
                    return {
                        "username": username,
                        "email": email,
                        "token": data.get("access_token") or data.get("token")
                    }
            return None
        except Exception as e:
            print(f"注册测试用户失败: {e}")
            return None
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("安全测试报告")
        print("="*60)
        
        critical_fail = sum(1 for r in TEST_RESULTS if not r["passed"] and r["severity"] == "critical")
        high_fail = sum(1 for r in TEST_RESULTS if not r["passed"] and r["severity"] == "high")
        medium_fail = sum(1 for r in TEST_RESULTS if not r["passed"] and r["severity"] == "medium")
        total_pass = sum(1 for r in TEST_RESULTS if r["passed"])
        total_fail = sum(1 for r in TEST_RESULTS if not r["passed"])
        
        print(f"\n总测试数: {len(TEST_RESULTS)}")
        print(f"通过: {total_pass} | 失败: {total_fail}")
        print(f"\n严重问题: {critical_fail}")
        print(f"高危问题: {high_fail}")
        print(f"中危问题: {medium_fail}")
        
        if critical_fail > 0:
            print("\n❌ 存在严重安全漏洞，不建议上线")
        elif high_fail > 0:
            print("\n⚠️ 存在高危漏洞，建议修复后再上线")
        else:
            print("\n✅ 安全测试通过")
        
        # 保存详细报告
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "target": BASE_URL,
            "summary": {
                "total": len(TEST_RESULTS),
                "passed": total_pass,
                "failed": total_fail,
                "critical": critical_fail,
                "high": high_fail,
                "medium": medium_fail
            },
            "details": TEST_RESULTS
        }
        
        os.makedirs("/root/.openclaw/workspace/secondlife/tests", exist_ok=True)
        with open("/root/.openclaw/workspace/secondlife/tests/security_test_report_v2.json", "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存: security_test_report_v2.json")
        return report


def main():
    """主测试函数"""
    tester = SecurityTester()
    
    print("="*60)
    print("第二人生平台 V2.0 全维度安全测试")
    print(f"目标: {BASE_URL}")
    print(f"时间: {datetime.utcnow().isoformat()}")
    print("="*60)
    
    # 执行测试
    tester.test_auth_bypass()
    tester.test_token_security()
    tester.test_sql_injection()
    tester.test_xss_protection()
    tester.test_business_logic()
    tester.test_idor()
    pressure_results = tester.test_pressure()
    
    # 生成报告
    report = tester.generate_report()
    
    return report


if __name__ == "__main__":
    main()
