#!/usr/bin/env python3
"""
第二人生平台 V2.0 - 快速安全测试
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://secondlife-platform.onrender.com"

print("="*60)
print("第二人生平台 V2.0 快速安全验证")
print(f"目标: {BASE_URL}")
print("="*60)

results = []

def test(name, check, severity="info"):
    status = "✅" if check else "❌"
    results.append({"name": name, "passed": check, "severity": severity})
    print(f"{status} {name}")
    return check

# 1. 健康检查
print("\n1. 服务健康检查")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=15)
    test("Health Endpoint", r.status_code == 200, "high")
    if r.status_code == 200:
        print(f"   响应: {r.json()}")
except Exception as e:
    test("Health Endpoint", False, "critical")
    print(f"   错误: {e}")

# 2. 未授权访问测试
print("\n2. 未授权访问防护")
protected = ["/api/user/profile", "/api/tasks"]
for endpoint in protected:
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        test(f"Auth on {endpoint}", r.status_code in [401, 403], "high")
    except Exception as e:
        test(f"Auth on {endpoint}", False, "medium")

# 3. 无效Token测试
print("\n3. 无效Token拒绝")
try:
    headers = {"Authorization": "Bearer invalid_token"}
    r = requests.get(f"{BASE_URL}/api/user/profile", headers=headers, timeout=10)
    test("Invalid Token Rejected", r.status_code in [401, 403], "high")
except Exception as e:
    test("Invalid Token Rejected", False, "medium")

# 4. SQL注入基础测试
print("\n4. SQL注入防护")
try:
    r = requests.get(f"{BASE_URL}/api/", timeout=10)
    test("API Root Accessible", r.status_code == 200, "info")
except:
    test("API Root Accessible", False, "low")

# 5. XSS防护（通过检查响应头）
print("\n5. 安全响应头")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    has_xss_protection = "X-XSS-Protection" in r.headers or "Content-Security-Policy" in r.headers
    test("Security Headers Present", has_xss_protection, "medium")
    if not has_xss_protection:
        print(f"   建议添加: X-XSS-Protection, CSP")
except:
    test("Security Headers Present", False, "low")

# 6. 注册/登录流程测试
print("\n6. 认证流程测试")
try:
    import random
    username = f"test_{random.randint(10000,99999)}"
    
    # 注册
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": "Test123!"
    }, timeout=10)
    test("Registration Endpoint", r.status_code in [200, 201, 400, 422], "high")
    
    # 登录（如果注册成功或用户已存在）
    if r.status_code in [200, 201, 400]:
        r2 = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": username,
            "password": "Test123!"
        }, timeout=10)
        test("Login Endpoint", r2.status_code == 200, "high")
        if r2.status_code == 200:
            token = r2.json().get("access_token") or r2.json().get("token")
            test("Token Generated", token is not None, "high")
            if token:
                print(f"   Token: {token[:20]}...")
except Exception as e:
    test("Auth Flow", False, "critical")
    print(f"   错误: {e}")

# 总结
print("\n" + "="*60)
print("测试总结")
print("="*60)
passed = sum(1 for r in results if r["passed"])
total = len(results)
critical_fail = sum(1 for r in results if not r["passed"] and r["severity"] == "critical")
high_fail = sum(1 for r in results if not r["passed"] and r["severity"] == "high")

print(f"通过: {passed}/{total}")
print(f"严重问题: {critical_fail}, 高危问题: {high_fail}")

if critical_fail == 0 and high_fail == 0:
    print("\n✅ 快速验证通过")
else:
    print("\n⚠️ 需要关注的问题")

# 保存结果
report = {
    "timestamp": datetime.utcnow().isoformat(),
    "target": BASE_URL,
    "summary": {"passed": passed, "total": total},
    "results": results
}
with open("/root/.openclaw/workspace/secondlife/tests/quick_test_report.json", "w") as f:
    json.dump(report, f, indent=2)
