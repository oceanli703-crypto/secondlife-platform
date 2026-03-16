#!/usr/bin/env python3
"""
第二人生平台 - 测试执行入口
================================
一键执行所有测试
"""

import subprocess
import sys
import os
from datetime import datetime

def run_test(script_name, description):
    """运行单个测试脚本"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"{'='*60}")
    
    script_path = f"/root/.openclaw/workspace/secondlife/tests/{script_name}"
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⚠️  {description} 超时")
        return False
    except Exception as e:
        print(f"❌ {description} 失败: {e}")
        return False

def main():
    print("="*60)
    print("第二人生平台 - 全面测试执行")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("deploy_diagnostic.py", "部署诊断"),
        ("comprehensive_test.py", "全面功能测试"),
        ("load_test.py", "压力测试"),
        ("payment_test.py", "支付测试"),
    ]
    
    results = {}
    for script, desc in tests:
        results[desc] = run_test(script, desc)
    
    print("\n" + "="*60)
    print("测试执行完成")
    print("="*60)
    
    for desc, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {desc}")
    
    print("\n📄 测试报告位置:")
    print("  - /root/.openclaw/workspace/secondlife/tests/test_report.md")
    print("  - /root/.openclaw/workspace/secondlife/tests/test_report.json")
    print("  - /root/.openclaw/workspace/secondlife/tests/deployment_diagnostic.json")

if __name__ == "__main__":
    main()
