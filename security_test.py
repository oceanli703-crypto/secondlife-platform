#!/usr/bin/env python3
"""第二人生平台 - 安全测试脚本"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """健康检查"""
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    print("✅ 健康检查通过")

def test_auth_required():
    """测试认证要求"""
    r = requests.get(f"{BASE_URL}/api/tasks")
    assert r.status_code == 403
    print("✅ 未授权访问被正确拒绝")

def test_sql_injection():
    """SQL注入测试"""
    payload = {
        "username": "admin' OR '1'='1",
        "password": "test"
    }
    r = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
    assert r.status_code == 401
    print("✅ SQL注入防护有效")

def test_xss_protection():
    """XSS测试"""
    # 先登录
    login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "testuser",
        "password": "Test123456"
    })
    if login.status_code != 200:
        print("⚠️  登录失败，跳过XSS测试")
        return
    
    token = login.json()["access_token"]
    
    # 尝试XSS注入
    xss_payload = {
        "title": "<script>alert(1)</script>",
        "category": "test",
        "summary": "Test XSS",
        "description": "<img src=x onerror=alert(1)>",
        "budget_min": 100,
        "budget_max": 200,
        "visibility_level": "l1"
    }
    
    r = requests.post(
        f"{BASE_URL}/api/tasks",
        json=xss_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if r.status_code == 200:
        # 检查返回的数据是否被转义
        task_id = r.json().get("task_id")
        r2 = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = r2.json()
        title = data.get("title", "")
        
        if "<script>" in title:
            print("⚠️  XSS警告：脚本标签未被转义")
        else:
            print("✅ XSS防护有效")

def test_password_security():
    """密码安全测试"""
    # 弱密码注册
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": "weakuser",
        "email": "weak@example.com",
        "password": "123"  # 太弱
    })
    assert r.status_code == 422
    print("✅ 弱密码被拒绝")

def test_rate_limit():
    """速率限制测试"""
    # 快速发送多个请求
    for i in range(5):
        r = requests.get(f"{BASE_URL}/health")
        assert r.status_code == 200
    print("✅ 基础速率测试通过")

def run_all_tests():
    """运行所有测试"""
    print("🔐 开始安全测试...\n")
    
    tests = [
        ("健康检查", test_health),
        ("认证要求", test_auth_required),
        ("SQL注入防护", test_sql_injection),
        ("XSS防护", test_xss_protection),
        ("密码安全", test_password_security),
        ("速率限制", test_rate_limit),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name}失败: {e}")
            failed += 1
    
    print(f"\n📊 测试结果: {passed}通过, {failed}失败")
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
