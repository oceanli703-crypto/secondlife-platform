#!/usr/bin/env python3
"""
第二人生平台 - Render部署诊断与修复工具
"""

import subprocess
import requests
import time
import json
import os
from datetime import datetime

RENDER_URL = "https://secondlife-api.onrender.com"
RENDER_DASHBOARD = "https://dashboard.render.com"

class DeploymentDiagnostic:
    """部署诊断类"""
    
    def __init__(self):
        self.issues = []
        self.fixes = []
    
    def log(self, msg):
        print(f"[诊断] {msg}")
    
    def check_connectivity(self):
        """检查网络连通性"""
        self.log("检查网络连通性...")
        try:
            # 使用ping检查基本连通性
            result = subprocess.run(
                ["ping", "-c", "3", "secondlife-api.onrender.com"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self.log("✅ 网络连通性正常")
                return True
            else:
                self.log("⚠️  网络连通性问题")
                self.issues.append("网络连通性问题")
                return False
        except Exception as e:
            self.log(f"❌ 网络检查异常: {e}")
            return False
    
    def check_render_status(self):
        """检查Render服务状态"""
        self.log("检查Render服务状态...")
        
        symptoms = []
        
        # 尝试连接健康检查端点
        try:
            resp = requests.get(f"{RENDER_URL}/health", timeout=30)
            if resp.status_code == 200:
                self.log("✅ Render服务正常运行")
                return {"status": "healthy", "response": resp.json()}
        except requests.exceptions.Timeout:
            symptoms.append("连接超时 - Render服务可能处于休眠状态")
        except requests.exceptions.ConnectionError:
            symptoms.append("连接被拒绝 - 服务可能已停止或配置错误")
        except Exception as e:
            symptoms.append(f"其他错误: {str(e)}")
        
        self.log(f"⚠️  Render服务异常: {symptoms}")
        self.issues.extend(symptoms)
        
        return {"status": "unhealthy", "symptoms": symptoms}
    
    def diagnose_render_sleep(self):
        """诊断Render休眠问题"""
        self.log("诊断Render休眠状态...")
        
        # Render免费版会在15分钟无活动后休眠
        # 第一次请求可能需要30-60秒唤醒
        
        self.log("尝试唤醒Render服务...")
        start = time.time()
        
        try:
            resp = requests.get(f"{RENDER_URL}/health", timeout=60)
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                self.log(f"✅ 服务已唤醒，耗时 {elapsed:.1f}秒")
                self.fixes.append(f"Render服务从休眠中唤醒，耗时 {elapsed:.1f}秒")
                return True
        except requests.exceptions.Timeout:
            self.log("❌ 唤醒超时(60秒)，服务可能存在其他问题")
            self.issues.append("Render服务唤醒超时，可能需要手动检查")
        except Exception as e:
            self.log(f"❌ 唤醒失败: {e}")
        
        return False
    
    def check_backend_logs(self):
        """检查后端日志（模拟）"""
        self.log("检查后端日志...")
        
        # 实际需要在Render Dashboard查看
        log_info = {
            "source": "Render Dashboard",
            "url": f"{RENDER_DASHBOARD}/web/services",
            "note": "请登录Render Dashboard查看详细日志"
        }
        
        self.log(f"日志位置: {log_info['url']}")
        return log_info
    
    def suggest_fixes(self):
        """提供修复建议"""
        self.log("生成修复建议...")
        
        suggestions = []
        
        if "连接超时" in str(self.issues):
            suggestions.append({
                "priority": "HIGH",
                "issue": "Render服务休眠",
                "solution": "服务处于休眠状态，第一次请求需要30-60秒唤醒",
                "action": "等待服务唤醒，或升级到付费版保持服务始终运行"
            })
        
        if "连接被拒绝" in str(self.issues):
            suggestions.append({
                "priority": "CRITICAL",
                "issue": "服务可能已停止",
                "solution": "需要手动在Render Dashboard启动服务",
                "action": "1. 登录 https://dashboard.render.com\n2. 找到 secondlife-api 服务\n3. 点击 'Manual Deploy' 或重启服务"
            })
        
        suggestions.append({
            "priority": "MEDIUM",
            "issue": "免费版限制",
            "solution": "Render免费版有休眠限制，影响用户体验",
            "action": "考虑升级到Starter计划($7/月)保持服务始终运行"
        })
        
        return suggestions
    
    def generate_diagnostic_report(self):
        """生成诊断报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "target": RENDER_URL,
            "issues": self.issues,
            "fixes_applied": self.fixes,
            "suggestions": self.suggest_fixes()
        }
        
        with open("/root/.openclaw/workspace/secondlife/tests/deployment_diagnostic.json", "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    def run(self):
        """运行诊断"""
        print("="*60)
        print("第二人生平台 - Render部署诊断")
        print("="*60)
        
        # 检查连通性
        self.check_connectivity()
        
        # 检查Render状态
        status = self.check_render_status()
        
        if status["status"] == "unhealthy":
            # 尝试修复
            self.diagnose_render_sleep()
        
        # 检查日志
        self.check_backend_logs()
        
        # 生成报告
        report = self.generate_diagnostic_report()
        
        # 输出总结
        print("\n" + "="*60)
        print("诊断总结")
        print("="*60)
        
        if report["issues"]:
            print(f"发现问题: {len(report['issues'])}")
            for issue in report["issues"]:
                print(f"  - {issue}")
        else:
            print("✅ 未发现明显问题")
        
        if report["fixes_applied"]:
            print(f"\n已应用的修复:")
            for fix in report["fixes_applied"]:
                print(f"  - {fix}")
        
        print(f"\n修复建议:")
        for suggestion in report["suggestions"]:
            print(f"\n[{suggestion['priority']}] {suggestion['issue']}")
            print(f"  解决方案: {suggestion['solution']}")
            print(f"  操作: {suggestion['action']}")
        
        print(f"\n详细报告已保存至: /root/.openclaw/workspace/secondlife/tests/deployment_diagnostic.json")
        
        return report


if __name__ == "__main__":
    diagnostic = DeploymentDiagnostic()
    diagnostic.run()
