# -*- coding: utf-8 -*-
"""
Run_All_Figures.py
批量绘图与收集调度器 (Batch Plotting & Collection Orchestrator)
功能：
1. 自动扫描并执行所有绘图脚本。
2. 自动收集所有生成的 PDF 到 Paper_Figures/Paste 文件夹。
"""

import os
import sys
import time
import shutil
import subprocess
from datetime import timedelta

# --- 颜色控制 ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def collect_pdfs(source_root="Paper_Figures", target_folder="Paste"):
    """
    收集模块：遍历 source_root 下所有 PDF，复制到 source_root/target_folder
    """
    dest_path = os.path.join(source_root, target_folder)
    os.makedirs(dest_path, exist_ok=True)
    
    print(f"\n{Colors.HEADER}{'='*60}")
    print(f"📂 启动自动收集 (Harvester) -> 目标: {dest_path}")
    print(f"{'='*60}{Colors.ENDC}")

    collected_count = 0
    
    # os.walk 递归遍历
    for root, dirs, files in os.walk(source_root):
        # ⚠️ 关键：跳过目标文件夹自身，防止递归死循环
        if os.path.abspath(root) == os.path.abspath(dest_path):
            continue
            
        for file in files:
            if file.lower().endswith(".pdf"):
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_path, file)
                
                try:
                    shutil.copy2(src_file, dst_file) # copy2 保留文件元数据
                    # print(f"   -> 复制: {file}") #以此减少刷屏，只显示最终结果
                    collected_count += 1
                except Exception as e:
                    print(f"{Colors.FAIL}   -> 复制失败 {file}: {e}{Colors.ENDC}")

    print(f"{Colors.OKGREEN}✅ 收集完成！共复制了 {collected_count} 个 PDF 文件。{Colors.ENDC}")

def run_all():
    current_script = os.path.basename(__file__)
    
    # --- 1. 定义排除名单 ---
    EXCLUDED_FILES = {
        'Science_Figure.py', 
        'Science_Figure_Template.py', # <--- 新增排除
        current_script
    }

    # --- 2. 扫描文件 ---
    target_files = []
    for f in os.listdir('.'):
        if f.endswith('.py') and 'Figure' in f:
            if f not in EXCLUDED_FILES:
                target_files.append(f)
    
    target_files.sort()
    total_count = len(target_files)

    if total_count == 0:
        print(f"{Colors.WARNING}⚠️  未找到任务文件。{Colors.ENDC}")
        return

    print(f"{Colors.HEADER}{'='*60}")
    print(f"🚀 开始批量绘图 - 队列: {total_count} 个任务")
    print(f"{'='*60}{Colors.ENDC}\n")

    results = []
    start_time_global = time.time()

    # --- 3. 执行绘图 ---
    for idx, filename in enumerate(target_files, 1):
        print(f"{Colors.OKBLUE}[{idx}/{total_count}] 执行: {filename} ...{Colors.ENDC}")
        start_time = time.time()
        
        try:
            # 启动子进程，环境隔离
            subprocess.run([sys.executable, filename], check=True)
            status = "SUCCESS"
            color = Colors.OKGREEN
        except subprocess.CalledProcessError:
            status = "FAILED"
            color = Colors.FAIL
        except Exception as e:
            status = "ERROR"
            color = Colors.FAIL
            
        elapsed = time.time() - start_time
        results.append((filename, status, elapsed))
        print(f"{color}   -> {status} ({elapsed:.2f}s){Colors.ENDC}")
        print("-" * 40)

    # --- 4. 统计与报告 ---
    success_count = sum(1 for r in results if r[1] == "SUCCESS")
    
    print(f"\n{Colors.HEADER}📊 执行摘要{Colors.ENDC}")
    for fname, stat, elap in results:
        c = Colors.OKGREEN if stat == "SUCCESS" else Colors.FAIL
        print(f"{fname:<30} : {c}{stat}{Colors.ENDC} ({elap:.2f}s)")

    # --- 5. 触发收集 (仅当有任务成功时) ---
    if success_count > 0:
        collect_pdfs(source_root="Paper_Figures", target_folder="Paste")
    else:
        print(f"\n{Colors.WARNING}⚠️ 无成功任务，跳过收集步骤。{Colors.ENDC}")

    if success_count < total_count:
        sys.exit(1)

if __name__ == "__main__":
    run_all()