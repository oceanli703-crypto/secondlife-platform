#!/usr/bin/env python3
"""功能与性能测试"""

import requests
import time
import concurrent.futures

BASE_URL = "http://localhost:8000"
TOKEN = None

def login():
    """登录获取token"""
    global TOKEN
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "testuser",
        "password": "Test123456"
    })
    if r.status_code == 200:
        TOKEN = r.json()["access_token"]
        return True
    return False

def test_create_task():
    """测试创建任务"""
    r = requests.post(f"{BASE_URL}/api/tasks", json={
        "title": "企业官网UI设计",
        "category": "design",
        "summary": "需要重新设计公司官网，要求现代简洁风格",
        "description": "详细需求：响应式设计、品牌色调调整",
        "budget_min": 8000,
        "budget_max": 15000,
        "visibility_level": "l1"
    }, headers={"Authorization": f"Bearer {TOKEN}"})
    return r.status_code == 200

def test_list_tasks():
    """测试获取任务列表"""
    r = requests.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {TOKEN}"})
    return r.status_code == 200 and len(r.json()) > 0

def test_task_detail():
    """测试任务详情"""
    # 先获取列表
    r = requests.get(f"{BASE_URL}/api/tasks", headers={"Authorization": f"Bearer {TOKEN}"})
    tasks = r.json()
    if not tasks:
        return False
    
    # 获取详情
    task_id = tasks[0]["id"]
    r = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers={"Authorization": f"Bearer {TOKEN}"})
    return r.status_code == 200

def stress_test():
    """压力测试"""
    print("\n🔥 压力测试 (50并发请求)...")
    
    def make_request(i):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            return r.status_code == 200
        except:
            return False
    
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(make_request, range(50)))
    
    duration = time.time() - start
    success_rate = sum(results) / len(results) * 100
    
    print(f"✅ 成功率: {success_rate:.1f}%")
    print(f"⏱️  总耗时: {duration:.2f}s")
    print(f"⚡ 平均响应: {duration/50*1000:.1f}ms")
    
    return success_rate >= 95

def main():
    print("🧪 功能与性能测试\n")
    
    # 登录
    if not login():
        print("❌ 登录失败")
        return False
    print("✅ 登录成功")
    
    # 功能测试
    tests = [
        ("创建任务", test_create_task),
        ("任务列表", test_list_tasks),
        ("任务详情", test_task_detail),
    ]
    
    for name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {name}通过")
            else:
                print(f"❌ {name}失败")
        except Exception as e:
            print(f"❌ {name}异常: {e}")
    
    # 压力测试
    stress_test()
    
    print("\n✨ 测试完成")

if __name__ == "__main__":
    main()
