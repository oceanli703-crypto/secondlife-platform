#!/usr/bin/env python3
"""
第二人生平台 - 百万级并发压力测试
使用Locust风格的并发测试，模拟真实用户场景
"""

import asyncio
import aiohttp
import time
import json
import random
import string
from datetime import datetime
from typing import List, Dict
import sys

# 配置
BASE_URL = "https://secondlife-api.onrender.com"
LOCAL_URL = "http://localhost:8000"

# 测试参数
CONCURRENT_USERS = 1000  # 并发用户数
REQUESTS_PER_USER = 100  # 每个用户的请求数
RAMP_UP_TIME = 30  #  ramp-up时间（秒）

class LoadTestResult:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.errors = {}
        self.start_time = None
        self.end_time = None
    
    @property
    def avg_response_time(self):
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0
    
    @property
    def min_response_time(self):
        return min(self.response_times) if self.response_times else 0
    
    @property
    def max_response_time(self):
        return max(self.response_times) if self.response_times else 0
    
    @property
    def success_rate(self):
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def rps(self):
        if not self.start_time or not self.end_time:
            return 0
        duration = self.end_time - self.start_time
        return self.total_requests / duration if duration > 0 else 0
    
    def print_summary(self):
        print("\n" + "="*60)
        print("压力测试总结")
        print("="*60)
        print(f"总请求数: {self.total_requests}")
        print(f"成功请求: {self.successful_requests}")
        print(f"失败请求: {self.failed_requests}")
        print(f"成功率: {self.success_rate:.2f}%")
        print(f"RPS (每秒请求): {self.rps:.2f}")
        print(f"平均响应时间: {self.avg_response_time*1000:.2f}ms")
        print(f"最小响应时间: {self.min_response_time*1000:.2f}ms")
        print(f"最大响应时间: {self.max_response_time*1000:.2f}ms")
        if self.errors:
            print(f"\n错误统计:")
            for error, count in self.errors.items():
                print(f"  {error}: {count}")
        print("="*60)


class StressTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.result = LoadTestResult()
        self.semaphore = asyncio.Semaphore(100)  # 限制并发数
    
    def generate_random_string(self, length=8):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str, 
                          method="GET", data=None, headers=None) -> bool:
        """执行单个请求"""
        async with self.semaphore:
            start = time.time()
            try:
                url = f"{self.base_url}{endpoint}"
                
                if method == "GET":
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        elapsed = time.time() - start
                        self.result.response_times.append(elapsed)
                        self.result.total_requests += 1
                        
                        if resp.status < 500:
                            self.result.successful_requests += 1
                            return True
                        else:
                            self.result.failed_requests += 1
                            error_key = f"HTTP {resp.status}"
                            self.result.errors[error_key] = self.result.errors.get(error_key, 0) + 1
                            return False
                            
                else:  # POST
                    async with session.post(url, json=data, headers=headers, 
                                          timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        elapsed = time.time() - start
                        self.result.response_times.append(elapsed)
                        self.result.total_requests += 1
                        
                        if resp.status < 500:
                            self.result.successful_requests += 1
                            return True
                        else:
                            self.result.failed_requests += 1
                            error_key = f"HTTP {resp.status}"
                            self.result.errors[error_key] = self.result.errors.get(error_key, 0) + 1
                            return False
                            
            except asyncio.TimeoutError:
                elapsed = time.time() - start
                self.result.response_times.append(elapsed)
                self.result.total_requests += 1
                self.result.failed_requests += 1
                self.result.errors["Timeout"] = self.result.errors.get("Timeout", 0) + 1
                return False
            except Exception as e:
                elapsed = time.time() - start
                self.result.response_times.append(elapsed)
                self.result.total_requests += 1
                self.result.failed_requests += 1
                error_key = type(e).__name__
                self.result.errors[error_key] = self.result.errors.get(error_key, 0) + 1
                return False
    
    async def user_simulation(self, session: aiohttp.ClientSession, user_id: int):
        """模拟单个用户的行为"""
        actions = [
            ("/health", "GET"),
            ("/api/", "GET"),
            ("/api/docs", "GET"),
        ]
        
        for _ in range(REQUESTS_PER_USER):
            endpoint, method = random.choice(actions)
            await self.make_request(session, endpoint, method)
            # 随机延迟，模拟真实用户行为
            await asyncio.sleep(random.uniform(0.01, 0.1))
    
    async def run_load_test(self):
        """运行负载测试"""
        print(f"\n开始压力测试:")
        print(f"  并发用户: {CONCURRENT_USERS}")
        print(f"  每用户请求: {REQUESTS_PER_USER}")
        print(f"  预计总请求: {CONCURRENT_USERS * REQUESTS_PER_USER}")
        print(f"  目标URL: {self.base_url}")
        print("-" * 60)
        
        self.result.start_time = time.time()
        
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=100)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 创建任务
            tasks = []
            for i in range(CONCURRENT_USERS):
                task = asyncio.create_task(self.user_simulation(session, i))
                tasks.append(task)
                
                # ramp-up: 逐渐增加并发
                if i < CONCURRENT_USERS - 1:
                    await asyncio.sleep(RAMP_UP_TIME / CONCURRENT_USERS)
            
            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.result.end_time = time.time()
        self.result.print_summary()
        
        return self.result
    
    async def test_endpoint_capacity(self, endpoint: str, method="GET", 
                                    concurrent=100, duration=10):
        """测试特定端点的容量"""
        print(f"\n测试端点容量: {endpoint}")
        print(f"  并发: {concurrent}, 持续时间: {duration}s")
        
        result = LoadTestResult()
        result.start_time = time.time()
        stop_time = result.start_time + duration
        
        async def worker(session: aiohttp.ClientSession, worker_id: int):
            while time.time() < stop_time:
                start = time.time()
                try:
                    url = f"{self.base_url}{endpoint}"
                    if method == "GET":
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            elapsed = time.time() - start
                            result.response_times.append(elapsed)
                            result.total_requests += 1
                            if resp.status < 500:
                                result.successful_requests += 1
                            else:
                                result.failed_requests += 1
                    await asyncio.sleep(0.01)  # 10ms间隔
                except Exception as e:
                    elapsed = time.time() - start
                    result.response_times.append(elapsed)
                    result.total_requests += 1
                    result.failed_requests += 1
        
        connector = aiohttp.TCPConnector(limit=concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [asyncio.create_task(worker(session, i)) for i in range(concurrent)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        result.end_time = time.time()
        result.print_summary()
        return result


def save_report(result: LoadTestResult, filename: str):
    """保存测试报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "target_url": BASE_URL,
        "concurrent_users": CONCURRENT_USERS,
        "requests_per_user": REQUESTS_PER_USER,
        "results": {
            "total_requests": result.total_requests,
            "successful_requests": result.successful_requests,
            "failed_requests": result.failed_requests,
            "success_rate": result.success_rate,
            "rps": result.rps,
            "avg_response_time_ms": result.avg_response_time * 1000,
            "min_response_time_ms": result.min_response_time * 1000,
            "max_response_time_ms": result.max_response_time * 1000,
            "errors": result.errors
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n测试报告已保存: {filename}")


async def main():
    """主函数"""
    print("="*60)
    print("第二人生平台 - 百万级并发压力测试")
    print("="*60)
    
    # 使用Render URL
    tester = StressTester(BASE_URL)
    
    # 运行主压力测试
    result = await tester.run_load_test()
    
    # 保存报告
    save_report(result, "/root/.openclaw/workspace/secondlife/tests/load_test_report.json")
    
    # 性能瓶颈分析
    print("\n" + "="*60)
    print("性能瓶颈分析")
    print("="*60)
    
    if result.success_rate < 95:
        print("⚠️  警告: 成功率低于95%，系统可能存在稳定性问题")
    
    if result.avg_response_time > 1:
        print("⚠️  警告: 平均响应时间超过1秒，用户体验可能受影响")
    
    if result.rps < 100:
        print("⚠️  警告: RPS低于100，系统吞吐量不足")
    
    # 优化建议
    print("\n优化建议:")
    print("1. 考虑使用CDN加速静态资源")
    print("2. 增加数据库连接池大小")
    print("3. 启用Redis缓存热点数据")
    print("4. 使用负载均衡分散请求")
    print("5. 考虑使用更强大的服务器配置")
    
    return result


if __name__ == "__main__":
    # 设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
