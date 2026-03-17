#!/usr/bin/env python3
"""
第二人生平台 V2.0 - 压力测试
"""

import requests
import concurrent.futures
import time
import json
from datetime import datetime

BASE_URL = "https://secondlife-platform.onrender.com"
CONCURRENT_REQUESTS = 100  # 并发数
TOTAL_REQUESTS = 1000      # 总请求数

def make_request(i):
    """单个请求"""
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/health", timeout=30)
        elapsed = time.time() - start
        return {
            "index": i,
            "status": resp.status_code,
            "time": elapsed,
            "success": resp.status_code == 200
        }
    except Exception as e:
        return {"index": i, "status": 0, "time": 0, "success": False, "error": str(e)}

def run_pressure_test():
    """执行压力测试"""
    print("="*60)
    print("第二人生平台 - 压力测试")
    print(f"目标: {BASE_URL}")
    print(f"并发数: {CONCURRENT_REQUESTS}")
    print(f"总请求: {TOTAL_REQUESTS}")
    print("="*60)
    
    start_time = time.time()
    
    # 执行并发请求
    print(f"\n开始发送{TOTAL_REQUESTS}个并发请求...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(make_request, i) for i in range(TOTAL_REQUESTS)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    total_time = time.time() - start_time
    
    # 分析结果
    success_count = sum(1 for r in results if r["success"])
    failed_count = TOTAL_REQUESTS - success_count
    success_rate = success_count / TOTAL_REQUESTS * 100
    
    success_times = [r["time"] for r in results if r["success"]]
    avg_time = sum(success_times) / len(success_times) if success_times else 0
    max_time = max(success_times) if success_times else 0
    min_time = min(success_times) if success_times else 0
    
    rps = TOTAL_REQUESTS / total_time
    
    # 打印结果
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    print(f"总请求数: {TOTAL_REQUESTS}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"总耗时: {total_time:.2f}s")
    print(f"RPS: {rps:.1f}")
    print(f"平均响应: {avg_time:.3f}s")
    print(f"最快响应: {min_time:.3f}s")
    print(f"最慢响应: {max_time:.3f}s")
    
    # 评估
    print("\n" + "="*60)
    if success_rate >= 95:
        print("✅ 压力测试通过")
        status = "PASS"
    elif success_rate >= 90:
        print("⚠️ 压力测试部分通过")
        status = "PARTIAL"
    else:
        print("❌ 压力测试失败")
        status = "FAIL"
    print("="*60)
    
    # 保存报告
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "target": BASE_URL,
        "config": {
            "concurrent": CONCURRENT_REQUESTS,
            "total": TOTAL_REQUESTS
        },
        "results": {
            "success": success_count,
            "failed": failed_count,
            "success_rate": success_rate,
            "total_time": total_time,
            "rps": rps,
            "avg_response_time": avg_time,
            "min_response_time": min_time,
            "max_response_time": max_time
        },
        "status": status
    }
    
    with open("/root/.openclaw/workspace/secondlife/tests/pressure_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n报告已保存: pressure_test_report.json")
    return report

if __name__ == "__main__":
    run_pressure_test()
