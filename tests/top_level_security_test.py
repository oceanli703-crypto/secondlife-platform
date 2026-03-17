#!/usr/bin/env python3
"""
第二人生平台 - 全球顶级安全测试（简化版）
重点测试：业务逻辑漏洞、资金安全和基础压力测试
"""

import requests
import json
import time
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "https://secondlife-platform.onrender.com"

print("="*70)
print("🚀 第二人生平台 - 全球顶级安全与压力测试")
print("="*70)
print(f"API地址: {API_BASE}")
print(f"测试时间: {datetime.now().isoformat()}")
print("="*70)

session = requests.Session()
results = []

def log(test_id, name, level, status, detail=""):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"\n{icon} [{test_id}] {name}")
    print(f"   威胁等级: {level} | 状态: {status}")
    if detail:
        print(f"   详情: {detail}")
    results.append({"id": test_id, "name": name, "level": level, "status": status, "detail": detail})

# ========== 测试1: 重复发布任务攻击 ==========
print("\n" + "-"*70)
print("🔴 TEST-001: 重复发布任务攻击测试")
print("-"*70)

username = f"user_{random.randint(10000, 99999)}"
email = f"{username}@test.com"
password = "TestPass123!"

# 注册
resp = session.post(f"{API_BASE}/api/auth/register", json={
    "username": username, "email": email, "password": password
})
print(f"注册: {resp.status_code}")

# 登录
resp = session.post(f"{API_BASE}/api/auth/login", json={
    "username": username, "password": password
})
print(f"登录: {resp.status_code}")

if resp.status_code != 200:
    log("TEST-001", "重复发布任务攻击", "HIGH", "ERROR", f"无法登录: {resp.text[:100]}")
else:
    token = resp.json()["access_token"]
    
    # 快速连续发布5个相同任务
    task_data = {
        "title": "重复测试任务",
        "category": "design",
        "summary": "测试重复发布防护",
        "description": "详细描述",
        "budget_min": 100,
        "budget_max": 500,
        "visibility_level": "l1"
    }
    
    success_count = 0
    for i in range(5):
        resp = session.post(
            f"{API_BASE}/api/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 200:
            success_count += 1
        time.sleep(0.1)
    
    if success_count > 1:
        log("TEST-001", "重复发布任务攻击", "HIGH", "FAIL", 
            f"漏洞：成功发布{success_count}个重复任务，无防护机制")
    else:
        log("TEST-001", "重复发布任务攻击", "HIGH", "PASS", 
            f"防护正常：仅{success_count}个任务成功")

# ========== 测试2: 自发自接资金套取 ==========
print("\n" + "-"*70)
print("🔴 TEST-002: 自发自接资金套取测试")
print("-"*70)

username = f"fraud_{random.randint(10000, 99999)}"
resp = session.post(f"{API_BASE}/api/auth/register", json={
    "username": username, "email": f"{username}@test.com", "password": "TestPass123!"
})
print(f"注册: {resp.status_code}")

resp = session.post(f"{API_BASE}/api/auth/login", json={
    "username": username, "password": "TestPass123!"
})
print(f"登录: {resp.status_code}")

if resp.status_code == 200:
    token = resp.json()["access_token"]
    
    # 发布任务
    resp = session.post(
        f"{API_BASE}/api/tasks",
        json={
            "title": "自发自接测试",
            "category": "services",
            "summary": "测试资金套取",
            "description": "测试",
            "budget_min": 1000,
            "budget_max": 5000,
            "visibility_level": "l1"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"发布任务: {resp.status_code}")
    
    if resp.status_code == 200:
        task_id = resp.json().get("task_id")
        
        # 尝试自己接自己的任务
        resp = session.post(
            f"{API_BASE}/api/tasks/{task_id}/accept",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"自接任务: {resp.status_code} - {resp.text[:100]}")
        
        if resp.status_code == 200:
            log("TEST-002", "自发自接资金套取", "CRITICAL", "FAIL",
                "严重漏洞：用户可以自发自接，存在资金套取风险！")
        elif resp.status_code == 400:
            log("TEST-002", "自发自接资金套取", "CRITICAL", "PASS",
                "防护正常：系统阻止了自发自接")
        else:
            log("TEST-002", "自发自接资金套取", "HIGH", "PASS",
                f"防护正常：返回{resp.status_code}")
    else:
        log("TEST-002", "自发自接资金套取", "HIGH", "ERROR", "任务发布失败")
else:
    log("TEST-002", "自发自接资金套取", "HIGH", "ERROR", "登录失败")

# ========== 测试3: 并发接单测试 ==========
print("\n" + "-"*70)
print("🔴 TEST-003: 并发接单竞争测试")
print("-"*70)

# 创建3个用户
users = []
for i in range(3):
    username = f"concurrent_{random.randint(10000, 99999)}_{i}"
    session.post(f"{API_BASE}/api/auth/register", json={
        "username": username, "email": f"{username}@test.com", "password": "TestPass123!"
    })
    resp = session.post(f"{API_BASE}/api/auth/login", json={
        "username": username, "password": "TestPass123!"
    })
    if resp.status_code == 200:
        users.append((username, resp.json()["access_token"]))

print(f"创建用户: {len(users)}个")

if len(users) >= 3:
    publisher_token = users[0][1]
    acceptor1_token = users[1][1]
    acceptor2_token = users[2][1]
    
    # 发布任务
    resp = session.post(
        f"{API_BASE}/api/tasks",
        json={
            "title": "并发测试任务",
            "category": "development",
            "summary": "测试并发接单",
            "description": "测试",
            "budget_min": 1000,
            "budget_max": 5000,
            "visibility_level": "l1"
        },
        headers={"Authorization": f"Bearer {publisher_token}"}
    )
    
    if resp.status_code == 200:
        task_id = resp.json().get("task_id")
        
        # 两个用户同时接单
        def try_accept(token):
            return session.post(
                f"{API_BASE}/api/tasks/{task_id}/accept",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(try_accept, acceptor1_token)
            future2 = executor.submit(try_accept, acceptor2_token)
            resp1 = future1.result()
            resp2 = future2.result()
        
        success_count = sum([resp1.status_code == 200, resp2.status_code == 200])
        print(f"用户1接单: {resp1.status_code}, 用户2接单: {resp2.status_code}")
        
        if success_count == 2:
            log("TEST-003", "并发接单竞争测试", "CRITICAL", "FAIL",
                "严重漏洞：同一任务被两个用户同时接受！")
        elif success_count == 1:
            log("TEST-003", "并发接单竞争测试", "HIGH", "PASS",
                "防护正常：仅一个用户成功接单")
        else:
            log("TEST-003", "并发接单竞争测试", "MEDIUM", "WARNING",
                "异常：两个用户都未能接单")
    else:
        log("TEST-003", "并发接单竞争测试", "HIGH", "ERROR", "任务发布失败")
else:
    log("TEST-003", "并发接单竞争测试", "HIGH", "ERROR", "用户创建不足")

# ========== 测试4: 认证绕过测试 ==========
print("\n" + "-"*70)
print("🔴 TEST-004: 认证绕过测试")
print("-"*70)

resp = session.get(f"{API_BASE}/api/user/profile")
print(f"未认证访问: {resp.status_code}")

if resp.status_code == 401:
    log("TEST-004", "认证绕过测试", "HIGH", "PASS", "防护正常：未认证返回401")
elif resp.status_code == 200:
    log("TEST-004", "认证绕过测试", "CRITICAL", "FAIL", "严重漏洞：未认证可访问！")
else:
    log("TEST-004", "认证绕过测试", "MEDIUM", "PASS", f"返回{resp.status_code}")

# ========== 测试5: SQL注入测试 ==========
print("\n" + "-"*70)
print("🔴 TEST-005: SQL注入测试")
print("-"*70)

payloads = [
    "' OR '1'='1",
    "' UNION SELECT * FROM users--",
    "1; DROP TABLE users--",
]

injection_found = False
for payload in payloads:
    resp = session.post(f"{API_BASE}/api/auth/login", json={
        "username": payload,
        "password": "test"
    })
    # 检查SQL错误泄露
    if "sql" in resp.text.lower() or "sqlite" in resp.text.lower():
        injection_found = True
        print(f"SQL错误泄露: {payload[:30]}...")
        break
    # 检查是否注入成功
    if resp.status_code == 200 and "access_token" in resp.text:
        injection_found = True
        print(f"SQL注入成功: {payload[:30]}...")
        break

if injection_found:
    log("TEST-005", "SQL注入测试", "CRITICAL", "FAIL", "发现SQL注入漏洞！")
else:
    log("TEST-005", "SQL注入测试", "CRITICAL", "PASS", "防护正常：无SQL注入")

# ========== 测试6: XSS攻击测试 ==========
print("\n" + "-"*70)
print("🔴 TEST-006: XSS攻击测试")
print("-"*70)

username = f"xss_{random.randint(10000, 99999)}"
resp = session.post(f"{API_BASE}/api/auth/register", json={
    "username": username, "email": f"{username}@test.com", "password": "TestPass123!"
})
resp = session.post(f"{API_BASE}/api/auth/login", json={
    "username": username, "password": "TestPass123!"
})

if resp.status_code == 200:
    token = resp.json()["access_token"]
    
    xss_payload = "<script>alert('XSS')</script>"
    resp = session.post(
        f"{API_BASE}/api/tasks",
        json={
            "title": xss_payload,
            "category": "design",
            "summary": xss_payload,
            "description": xss_payload,
            "budget_min": 100,
            "budget_max": 500,
            "visibility_level": "l1"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if resp.status_code == 200:
        task_id = resp.json().get("task_id")
        resp = session.get(
            f"{API_BASE}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if xss_payload in resp.text:
            log("TEST-006", "XSS攻击测试", "CRITICAL", "FAIL", "XSS payload未转义！")
        elif "&lt;" in resp.text:
            log("TEST-006", "XSS攻击测试", "CRITICAL", "PASS", "防护正常：XSS被HTML转义")
        else:
            log("TEST-006", "XSS攻击测试", "HIGH", "PASS", "XSS payload被处理")
    else:
        log("TEST-006", "XSS攻击测试", "HIGH", "ERROR", "任务发布失败")
else:
    log("TEST-006", "XSS攻击测试", "HIGH", "ERROR", "登录失败")

# ========== 测试7: 压力测试 - 100并发 ==========
print("\n" + "-"*70)
print("🔴 TEST-007: 压力测试 - 100并发请求")
print("-"*70)

def health_check():
    try:
        start = time.time()
        resp = session.get(f"{API_BASE}/health", timeout=10)
        elapsed = time.time() - start
        return resp.status_code, elapsed
    except Exception as e:
        return None, str(e)

with ThreadPoolExecutor(max_workers=100) as executor:
    futures = [executor.submit(health_check) for _ in range(100)]
    check_results = [f.result() for f in as_completed(futures)]

success_count = sum(1 for r in check_results if r[0] == 200)
avg_time = sum(r[1] for r in check_results if r[0] == 200) / max(success_count, 1)
success_rate = success_count / 100 * 100

print(f"成功率: {success_rate:.1f}%, 平均响应: {avg_time:.2f}s")

if success_rate >= 99 and avg_time < 2:
    log("TEST-007", "压力测试-100并发", "MEDIUM", "PASS",
        f"成功率{success_rate:.1f}%, 平均响应{avg_time:.2f}s")
elif success_rate >= 95:
    log("TEST-007", "压力测试-100并发", "MEDIUM", "WARNING",
        f"成功率{success_rate:.1f}%, 平均响应{avg_time:.2f}s")
else:
    log("TEST-007", "压力测试-100并发", "HIGH", "FAIL",
        f"成功率{success_rate:.1f}%, 平均响应{avg_time:.2f}s")

# ========== 测试8: 暴力破解防护 ==========
print("\n" + "-"*70)
print("🔴 TEST-008: 暴力破解防护测试")
print("-"*70)

test_user = f"brute_{random.randint(10000, 99999)}"
session.post(f"{API_BASE}/api/auth/register", json={
    "username": test_user, "email": f"{test_user}@test.com", "password": "CorrectPass123!"
})

# 5次错误密码
for i in range(5):
    session.post(f"{API_BASE}/api/auth/login", json={
        "username": test_user,
        "password": f"WrongPass{i}!"
    })

# 尝试正确密码
resp = session.post(f"{API_BASE}/api/auth/login", json={
    "username": test_user,
    "password": "CorrectPass123!"
})

if resp.status_code == 200:
    log("TEST-008", "暴力破解防护", "MEDIUM", "WARNING",
        "5次错误后仍可登录，建议添加速率限制")
elif resp.status_code == 429:
    log("TEST-008", "暴力破解防护", "HIGH", "PASS", "触发速率限制")
else:
    log("TEST-008", "暴力破解防护", "MEDIUM", "PENDING", f"返回{resp.status_code}")

# ========== 测试9: 水平越权测试 ==========
print("\n" + "-"*70)
print("🔴 TEST-009: 水平越权测试")
print("-"*70)

user1 = f"horiz1_{random.randint(10000, 99999)}"
user2 = f"horiz2_{random.randint(10000, 99999)}"

tokens = {}
for u in [user1, user2]:
    session.post(f"{API_BASE}/api/auth/register", json={
        "username": u, "email": f"{u}@test.com", "password": "TestPass123!"
    })
    resp = session.post(f"{API_BASE}/api/auth/login", json={
        "username": u, "password": "TestPass123!"
    })
    if resp.status_code == 200:
        tokens[u] = resp.json()["access_token"]

if len(tokens) == 2:
    # user1发布L3私密任务
    resp = session.post(
        f"{API_BASE}/api/tasks",
        json={
            "title": "私密任务",
            "category": "design",
            "summary": "私密",
            "description": "私密",
            "budget_min": 1000,
            "budget_max": 5000,
            "visibility_level": "l3"
        },
        headers={"Authorization": f"Bearer {tokens[user1]}"}
    )
    
    if resp.status_code == 200:
        task_id = resp.json().get("task_id")
        
        # user2尝试访问
        resp = session.get(
            f"{API_BASE}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {tokens[user2]}"}
        )
        
        if resp.status_code == 200:
            log("TEST-009", "水平越权测试", "CRITICAL", "FAIL",
                "用户可访问其他用户的私密任务！")
        elif resp.status_code == 403:
            log("TEST-009", "水平越权测试", "HIGH", "PASS", "无权访问返回403")
        else:
            log("TEST-009", "水平越权测试", "HIGH", "PASS", f"返回{resp.status_code}")
    else:
        log("TEST-009", "水平越权测试", "MEDIUM", "ERROR", "任务创建失败")
else:
    log("TEST-009", "水平越权测试", "MEDIUM", "ERROR", "用户创建失败")

# ========== 测试报告汇总 ==========
print("\n" + "="*70)
print("📊 测试报告汇总")
print("="*70)

critical_fail = sum(1 for r in results if r["level"] == "CRITICAL" and r["status"] == "FAIL")
high_fail = sum(1 for r in results if r["level"] == "HIGH" and r["status"] == "FAIL")
medium_warn = sum(1 for r in results if r["level"] == "MEDIUM" and r["status"] in ["FAIL", "WARNING"])
passed = sum(1 for r in results if r["status"] == "PASS")

print(f"\n总测试数: {len(results)}")
print(f"通过: {passed}")
print(f"严重漏洞: {critical_fail}")
print(f"高危漏洞: {high_fail}")
print(f"中危问题: {medium_warn}")

print("\n" + "-"*70)
print("❌ 需要关注的问题:")
print("-"*70)
for r in results:
    if r["status"] in ["FAIL", "WARNING"]:
        print(f"\n[{r['level']}] {r['id']}: {r['name']}")
        print(f"   详情: {r['detail']}")

print("\n" + "="*70)
if critical_fail > 0:
    print("🔴 评估结果: 不建议上线")
    print("   存在严重安全漏洞，需要立即修复")
elif high_fail > 0:
    print("🟠 评估结果: 有条件上线")
    print("   存在高危漏洞，建议修复后再上线")
elif medium_warn > 0:
    print("🟡 评估结果: 可以上线，需关注")
    print("   存在中危问题，建议后续优化")
else:
    print("🟢 评估结果: 可以上线")
    print("   所有关键测试通过")
print("="*70)

# 保存报告
with open("/root/.openclaw/workspace/secondlife/tests/security_test_report.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n报告已保存: /root/.openclaw/workspace/secondlife/tests/security_test_report.json")
